"""
WeArm 手柄操控 + 动作录制/回放

支持通过游戏手柄 (joystick/gamepad) 操控机械臂，
并录制动作序列为 JSON，后续可精确回放。

依赖: pygame (手柄读取) + pyserial (串口通信)

用法:
    # 手柄操控 + 录制
    python -m simulation.teach --port COM10 --record my_move.json

    # 仅录制（不发送到实物，纯仿真）
    python -m simulation.teach --simulate --record my_move.json

    # 回放录制好的动作
    python -m simulation.teach --replay my_move.json --port COM10

    # 仿真回放
    python -m simulation.teach --replay my_move.json --simulate

手柄映射 (默认 Xbox 布局):
    左摇杆 Y轴  → 底盘旋转 (舵机 0)
    左摇杆 X轴  → 大臂俯仰 (舵机 1)
    右摇杆 Y轴  → 小臂俯仰 (舵机 2)
    右摇杆 X轴  → 手腕旋转 (舵机 3)
    A 按钮      → 夹爪闭合 (舵机 4, PWM 2000)
    B 按钮      → 夹爪张开 (舵机 4, PWM 1500)
    Y 按钮      → 执行盖章序列
    START       → 保存录制并退出
    LB / RB     → 所有舵机回中位
"""

import sys
import os
import time
import json
import math
import argparse
import threading
from collections import OrderedDict

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_project_root, "apps", "backend"))

from hardware.kinematics import (
    H0, L1, L2, L3,
    pwm_to_deg, deg_to_pwm,
    inverse_kinematics, forward_kinematics,
)

# ─── 常量 ──────────────────────────────────────────────────────────────────

PWM_MIN = 500
PWM_MAX = 2500
PWM_MID = 1500
SERVO_NAMES = {0: "底盘", 1: "大臂", 2: "小臂", 3: "手腕", 4: "夹爪", 5: "辅助"}

# ─── 手柄映射 ──────────────────────────────────────────────────────────────

# 每个舵机由哪个轴控制，以及灵敏度
AXIS_MAP = {
    0: {"axis": 1, "scale": 200, "label": "底盘"},   # 左摇杆 Y
    1: {"axis": 0, "scale": 200, "label": "大臂"},   # 左摇杆 X
    2: {"axis": 3, "scale": 200, "label": "小臂"},   # 右摇杆 Y
    3: {"axis": 2, "scale": 200, "label": "手腕"},   # 右摇杆 X
}

BUTTON_MAP = {
    0:  {"servo": 4, "pwm": 2000, "label": "夹爪闭合"},  # A
    1:  {"servo": 4, "pwm": 1500, "label": "夹爪张开"},  # B
    2:  {"servo": 4, "pwm": 1000, "label": "夹爪全开"},  # X
    3:  {"action": "stamp", "label": "盖章"},            # Y
    7:  {"action": "quit", "label": "保存退出"},          # START
    4:  {"action": "home", "label": "回中位"},            # LB
    5:  {"action": "home", "label": "回中位"},            # RB
}


# ─── 录制/回放 ────────────────────────────────────────────────────────────


class MotionRecorder:
    """录制机械臂动作序列"""

    def __init__(self):
        self.frames = []  # [{timestamp, pwm: {...}}]
        self.start_time = None

    def start(self):
        self.start_time = time.time()
        self.frames = []

    def record(self, pwm_state: dict):
        """记录一帧"""
        self.frames.append({
            "t": round(time.time() - self.start_time, 3),
            "pwm": dict(pwm_state),
        })

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "version": 1,
                "duration": round(time.time() - self.start_time, 1),
                "frames": self.frames,
            }, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 录制已保存: {path} ({len(self.frames)} 帧, "
              f"{self.frames[-1]['t']:.1f}s)")

    @staticmethod
    def load(path: str) -> list:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["frames"]


def replay_motion(frames: list, send_fn, speed: float = 1.0):
    """回放录制的动作

    send_fn(pwm_dict): 发送 PWM 到机械臂的函数
    speed: 回放速度倍率 (1.0 = 原速)
    """
    print(f"回放 {len(frames)} 帧, 速度 x{speed}...")
    print("按 Ctrl+C 停止\n")

    last_pwm = None
    start = time.time()

    try:
        for frame in frames:
            target_t = frame["t"] / speed
            elapsed = time.time() - start
            if target_t > elapsed:
                time.sleep(target_t - elapsed)

            pwm = frame["pwm"]
            # 只发送变化了的舵机（减少串口流量）
            if pwm != last_pwm:
                send_fn({int(k): int(v) for k, v in pwm.items()})
                last_pwm = pwm

            # 简单进度显示
            progress = frame["t"] / frames[-1]["t"] * 100
            print(f"\r  进度: {progress:5.1f}%  t={frame['t']:.1f}s", end="")

        print("\n✅ 回放完成")

    except KeyboardInterrupt:
        print("\n⏸ 回放已中断")


# ─── 串口发送 ──────────────────────────────────────────────────────────────


def make_serial_sender(port: str, baud: int = 115200):
    """创建串口发送函数"""
    import serial
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(1)

    def send(pwm_dict: dict):
        cmds = "".join(
            f"#{sid:03d}P{int(pwm):04d}T0800!"
            for sid, pwm in sorted(pwm_dict.items())
        )
        ser.write(f"{{{cmds}}}".encode())

    def close():
        ser.close()

    return send, close


def make_sim_sender():
    """创建仿真发送函数（只打印，不发送）"""

    def send(pwm_dict: dict):
        parts = []
        for sid, pwm in sorted(pwm_dict.items()):
            deg = pwm_to_deg(pwm)
            parts.append(f"{SERVO_NAMES[sid]}={pwm}({deg:.0f}°)")
        print(f"  [仿真] {' | '.join(parts)}")

    def close():
        pass

    return send, close


# ─── 手柄操控主循环 ────────────────────────────────────────────────────────


def teach_mode(port: str = None, record_path: str = None):
    """手柄示教模式"""
    try:
        import pygame
    except ImportError:
        print("请先安装 pygame: pip install pygame")
        return

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("❌ 未检测到手柄，请连接后重试")
        print("   (使用 --simulate 可在无实物/无手柄时测试)")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"✅ 手柄已连接: {joystick.get_name()}")
    print(f"   轴: {joystick.get_numaxes()}  按钮: {joystick.get_numbuttons()}")

    # 串口/仿真
    if port:
        send_fn, close_fn = make_serial_sender(port)
        print(f"✅ 串口已连接: {port}")
    else:
        send_fn, close_fn = make_sim_sender()
        print("⚠ 仿真模式 (不发送实物指令)")

    # 录制
    recorder = MotionRecorder() if record_path else None
    if recorder:
        recorder.start()
        print(f"🔴 录制中 → {record_path}")

    # 状态
    pwm_state = {i: PWM_MID for i in range(6)}
    running = True
    last_send = 0
    clock = pygame.time.Clock()

    print("\n操控说明:")
    print("  左摇杆 → 底盘/大臂    右摇杆 → 小臂/手腕")
    print("  A=夹爪闭合  B=张开  Y=盖章  START=保存退出  LB/RB=回中")
    print("  Ctrl+C 强制退出\n")

    def apply_axis(servo_id: int, axis_val: float):
        """将手柄轴值 (-1~1) 映射到 PWM 增量"""
        cfg = AXIS_MAP[servo_id]
        delta = int(axis_val * cfg["scale"])
        pwm_state[servo_id] = max(PWM_MIN, min(PWM_MAX, pwm_state[servo_id] + delta))

    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.JOYBUTTONDOWN:
                    btn = event.button
                    if btn in BUTTON_MAP:
                        action = BUTTON_MAP[btn]
                        if "servo" in action:
                            pwm_state[action["servo"]] = action["pwm"]
                            print(f"  [{action['label']}]: PWM={action['pwm']}")
                        elif action.get("action") == "stamp":
                            print("  [盖章序列] 执行中...")
                            # 记录当前位置，下压 100 PWM，再回位
                            orig = dict(pwm_state)
                            pwm_state[3] = min(PWM_MAX, pwm_state[3] + 130)
                            send_fn(pwm_state)
                            time.sleep(0.8)
                            pwm_state.update(orig)
                            print("  [盖章序列] 完成")
                        elif action.get("action") == "quit":
                            running = False
                            print("\n  [保存退出]")
                        elif action.get("action") == "home":
                            for i in range(6):
                                pwm_state[i] = PWM_MID
                            print("  [回中位]")

                elif event.type == pygame.JOYBUTTONUP:
                    pass  # 瞬时动作，无需处理

            # 持续读取摇杆轴
            for servo_id in AXIS_MAP:
                axis_idx = AXIS_MAP[servo_id]["axis"]
                if axis_idx < joystick.get_numaxes():
                    val = joystick.get_axis(axis_idx)
                    # 死区
                    if abs(val) < 0.1:
                        val = 0
                    apply_axis(servo_id, val)

            # 限速发送（每 80ms 一次）
            now = time.time()
            if now - last_send > 0.08:
                send_fn(pwm_state)
                if recorder:
                    recorder.record(pwm_state)
                last_send = now

            clock.tick(60)  # 60Hz 手柄轮询

    except KeyboardInterrupt:
        print("\n⏸ 操控已停止")
    finally:
        if recorder and record_path:
            recorder.save(record_path)
        # 回中位
        send_fn({i: PWM_MID for i in range(6)})
        time.sleep(0.5)
        close_fn()
        pygame.quit()


# ─── CLI ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="WeArm 手柄示教 + 动作录制/回放")
    parser.add_argument("--port", type=str, default=None,
                        help="串口号 (如 COM10)")
    parser.add_argument("--simulate", action="store_true",
                        help="仿真模式 (不连接实物)")
    parser.add_argument("--record", type=str, default=None,
                        help="录制动作到 JSON 文件")
    parser.add_argument("--replay", type=str, default=None,
                        help="回放 JSON 动作文件")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="回放速度倍率 (默认 1.0)")
    args = parser.parse_args()

    if args.replay:
        frames = MotionRecorder.load(args.replay)
        if args.simulate:
            send_fn, close_fn = make_sim_sender()
        elif args.port:
            send_fn, close_fn = make_serial_sender(args.port)
        else:
            print("回放需要 --port (串口) 或 --simulate (仿真)")
            return

        try:
            replay_motion(frames, send_fn, args.speed)
        finally:
            close_fn()
    else:
        port = None if args.simulate else args.port
        if not port and not args.simulate:
            print("请指定 --port (串口) 或 --simulate (仿真模式)")
            print("示例: python -m simulation.teach --port COM10 --record demo.json")
            return
        teach_mode(port, args.record)


if __name__ == "__main__":
    main()
