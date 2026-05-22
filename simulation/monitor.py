"""
WeArm 舵机角度/位置实时监控

由于 WeArm 使用标准舵机 (MG996R/DS3225)，无位置回读，
本脚本通过追踪最近一次发送的 PWM 指令来显示当前状态。

两种模式:
  1. 监听模式 (默认)  — 连接串口，拦截并记录所有发送的指令
  2. 独立查询模式     — 手动输入 PWM 值/坐标，即时显示计算结果

用法:
    python -m simulation.monitor                  # 监听模式 (需连接实物)
    python -m simulation.monitor --simulate       # 仿真模式 (手动输入 PWM)
    python -m simulation.monitor --ik 120 0 15    # IK 反算: 目标 → 关节角

前提: 已在项目根目录下
"""

import sys
import os
import time
import math
import argparse
import threading
from collections import OrderedDict

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_project_root, "apps", "backend"))

from hardware.kinematics import (
    H0, L1, L2, L3,
    pwm_to_deg,
    deg_to_pwm,
    inverse_kinematics,
    forward_kinematics,
)

# ─── 舵机信息 ──────────────────────────────────────────────────────────────

SERVO_NAMES = {0: "底盘", 1: "大臂", 2: "小臂", 3: "手腕", 4: "夹爪", 5: "辅助"}
PWM_MIN = 500
PWM_MAX = 2500
PWM_MID = 1500


# ─── 状态追踪器 ────────────────────────────────────────────────────────────


class ArmState:
    """记录机械臂当前状态: PWM → 角度 → 末端位置"""

    def __init__(self):
        # 默认中位
        self.pwm = {i: PWM_MID for i in range(6)}
        self._lock = threading.RLock()

    def update(self, positions: dict):
        """更新舵机 PWM 值"""
        with self._lock:
            for sid, pwm in positions.items():
                self.pwm[int(sid)] = int(pwm)

    def get_angles(self) -> dict:
        """返回各舵机角度 (度)"""
        with self._lock:
            return {sid: pwm_to_deg(pwm) for sid, pwm in self.pwm.items()}

    def get_end_effector(self) -> tuple | None:
        """通过正向运动学计算末端位置"""
        with self._lock:
            angles = self.get_angles()
            try:
                joints = forward_kinematics(angles)
                return joints[-1]  # (y, z)
            except Exception:
                return None

    def snapshot(self) -> str:
        """生成一行状态快照"""
        angles = self.get_angles()
        end = self.get_end_effector()

        lines = []
        lines.append("┌─────────────────────────────────────────────────────┐")
        header = "│ 舵机 │  名称  │  PWM   │  角度   │  说明           │"
        lines.append(header)

        for sid in range(6):
            name = SERVO_NAMES[sid]
            pwm = self.pwm[sid]
            deg = angles[sid]
            pct = (pwm - PWM_MIN) / (PWM_MAX - PWM_MIN) * 100
            bar = _make_bar(pct, 10)
            lines.append(
                f"│  {sid}   │ {name:6s} │ {pwm:5d} │ {deg:6.1f}° │ {bar} │"
            )

        lines.append("├─────────────────────────────────────────────────────┤")
        if end:
            lines.append(f"│ 末端位置: Y={end[0]:6.1f} mm  Z={end[1]:6.1f} mm         │")
        else:
            lines.append("│ 末端位置: 计算失败                                  │")
        lines.append(f"│ 连杆参数: H0={H0} L1={L1} L2={L2} L3={L3}                │")
        lines.append("└─────────────────────────────────────────────────────┘")
        return "\n".join(lines)


def _make_bar(pct: float, width: int) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ─── 监听模式（连接实物，捕获串口指令） ────────────────────────────────────


def monitor_serial(port: str, baud: int = 115200):
    """连接 WeArm 串口，显示并记录所有发送的指令"""
    import serial

    state = ArmState()

    try:
        ser = serial.Serial(port, baud, timeout=1)
        print(f"✅ 已连接 {port} @ {baud}")
    except Exception as e:
        print(f"❌ 无法连接串口: {e}")
        print("   回退到仿真模式...")
        return simulate_mode()

    print("正在监听 WeArm 指令... (Ctrl+C 退出)\n")

    # 启动一个线程读取串口回显（如果有的话）
    buffer = b""

    def read_loop():
        nonlocal buffer
        while True:
            try:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting)
                    buffer += data
                    # 尝试解析完整的指令
                    while b"!" in buffer:
                        idx = buffer.index(b"!")
                        cmd = buffer[: idx + 1]
                        buffer = buffer[idx + 1 :]
                        _parse_cmd(cmd.decode(errors="ignore"), state)
                else:
                    time.sleep(0.05)
            except (OSError, serial.SerialException):
                break

    reader = threading.Thread(target=read_loop, daemon=True)
    reader.start()

    last_display = 0
    try:
        while True:
            now = time.time()
            if now - last_display > 0.5:  # 每 0.5 秒刷新
                _clear_screen()
                print(state.snapshot())
                last_display = now
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n监控已停止。")
    finally:
        ser.close()


def _parse_cmd(cmd: str, state: ArmState):
    """解析 WeArm 指令: #{id}P{pwm}T{duration}!"""
    # 支持单条和多条 (用 { } 包裹)
    cmd = cmd.strip()
    if cmd.startswith("{") and cmd.endswith("}"):
        cmd = cmd[1:-1]

    import re
    pattern = r"#(\d{3})P(\d{4})T(\d{4})!"
    for match in re.finditer(pattern, cmd):
        sid = int(match.group(1))
        pwm = int(match.group(2))
        state.update({sid: pwm})


# ─── 仿真模式（手动输入） ──────────────────────────────────────────────────


def simulate_mode():
    """交互式手动输入 PWM 或坐标"""
    state = ArmState()

    print("WeArm 仿真监控 — 手动输入模式")
    print("  输入格式: <舵机ID> <PWM值>      例如: 1 920")
    print("            ik <x> <y> <z>        例如: ik 120 0 15")
    print("            help                   显示帮助")
    print("            q                      退出\n")

    while True:
        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not cmd:
            _clear_screen()
            print(state.snapshot())
            continue

        if cmd.lower() in ("q", "quit", "exit"):
            break

        if cmd.lower() == "help":
            print(__doc__)
            continue

        if cmd.lower().startswith("ik"):
            # IK 模式: ik <x> <y> <z>
            parts = cmd.split()
            if len(parts) < 4:
                print("用法: ik <x> <y> <z>  (单位: mm)")
                continue
            try:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
            except ValueError:
                print("坐标必须是数字")
                continue

            ik = inverse_kinematics(x, y, z)
            if ik is None:
                print(f"❌ 目标 ({x}, {y}, {z}) 超出工作空间")
                continue
            state.update(ik)
            angles = state.get_angles()
            print(f"✅ IK 结果: 底座={angles[0]:.1f}° 大臂={angles[1]:.1f}° "
                  f"小臂={angles[2]:.1f}° 手腕={angles[3]:.1f}°")
            print(f"   PWM: {ik}")
            print()

        else:
            # PWM 模式: <舵机ID> <PWM值>
            parts = cmd.split()
            if len(parts) < 2:
                print("格式: <舵机ID> <PWM值>")
                continue
            try:
                sid, pwm = int(parts[0]), int(parts[1])
            except ValueError:
                print("必须是整数")
                continue

            if sid not in range(6):
                print("舵机 ID: 0-5")
                continue
            pwm = max(PWM_MIN, min(PWM_MAX, pwm))
            state.update({sid: pwm})
            deg = pwm_to_deg(pwm)
            print(f"✅ 舵机 {sid} ({SERVO_NAMES[sid]}): PWM={pwm} → {deg:.1f}°")
            print()


def _clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


# ─── IK 快速查询 ──────────────────────────────────────────────────────────


def ik_query(x: float, y: float, z: float):
    """单次 IK 查询，直接打印结果"""
    print(f"目标坐标: ({x:.1f}, {y:.1f}, {z:.1f}) mm")
    print(f"连杆参数: H0={H0} L1={L1} L2={L2} L3={L3}\n")

    ik = inverse_kinematics(x, y, z)
    if ik is None:
        print("❌ 目标超出工作空间")
        return

    state = ArmState()
    state.update(ik)
    print(state.snapshot())


# ─── CLI ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="WeArm 舵机角度/位置监控")
    parser.add_argument("--port", type=str, default=None,
                        help="串口号 (如 /dev/ttyUSB0 或 COM10)")
    parser.add_argument("--simulate", action="store_true",
                        help="仿真交互模式 (不需要连接实物)")
    parser.add_argument("--ik", nargs=3, type=float, metavar=("X", "Y", "Z"),
                        help="单次 IK 查询: 目标坐标 (mm)")
    args = parser.parse_args()

    if args.ik:
        ik_query(args.ik[0], args.ik[1], args.ik[2])
    elif args.simulate:
        simulate_mode()
    elif args.port:
        monitor_serial(args.port)
    else:
        # 默认：尝试自动检测串口
        print("未指定模式，尝试自动检测串口...")
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        if ports:
            print(f"检测到串口: {ports[0].device}")
            monitor_serial(ports[0].device)
        else:
            print("未检测到串口，进入仿真模式。")
            simulate_mode()


if __name__ == "__main__":
    main()
