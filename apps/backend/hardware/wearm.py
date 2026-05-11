import time
import threading
import logging
from config import SERIAL_PORT, SERIAL_BAUD, SIMULATION_MODE

logger = logging.getLogger(__name__)

SERVO_NAMES = {0: "底盘", 1: "大臂", 2: "小臂", 3: "手腕", 4: "夹爪", 5: "辅助"}

PWM_MIN = 500
PWM_MAX = 2500
PWM_MID = 1500


def _cmd(servo_id: int, pwm: int, duration: int) -> bytes:
    return f"#{servo_id:03d}P{pwm:04d}T{duration:04d}!".encode()


def _cmd_multi(*cmds) -> bytes:
    body = "".join(f"#{i:03d}P{p:04d}T{t:04d}!" for i, p, t in cmds)
    return f"{{{body}}}".encode()


class WeArmController:
    """WeArm 机械臂控制器（PWM 文本协议，CH340，115200 波特率）"""

    _instance = None
    _ser = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not SIMULATION_MODE and self._ser is None:
            self._connect()
        elif SIMULATION_MODE:
            logger.info("[仿真模式] WeArmController 已初始化")

    def _connect(self):
        import serial

        try:
            self._ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=3)
            time.sleep(2)
            self._send(
                _cmd_multi(
                    (0, PWM_MID, 1000),
                    (1, PWM_MID, 1000),
                    (2, PWM_MID, 1000),
                    (3, PWM_MID, 1000),
                    (4, PWM_MID, 1000),
                    (5, PWM_MID, 1000),
                )
            )
            time.sleep(1.5)
            logger.info(f"WeArm 已连接: {SERIAL_PORT}")
        except Exception as e:
            raise RuntimeError(
                f"无法连接 WeArm（{SERIAL_PORT}）：{e}\n"
                "请检查：1) USB线是否插好  2) 电源开关是否打开  3) CH340驱动是否安装"
            )

    def _send(self, data: bytes):
        if SIMULATION_MODE:
            logger.info(f"[仿真] 发送: {data.decode()!r}")
            return
        with self._lock:
            if self._ser and self._ser.is_open:
                self._ser.write(data)

    def move_to(self, positions: dict, duration: int = 1000):
        """移动到指定 PWM 位置。positions: {servo_id: pwm_value}"""
        cmds = tuple((sid, int(pwm), duration) for sid, pwm in positions.items())
        self._send(_cmd_multi(*cmds))
        time.sleep(duration / 1000 + 0.3)

    def move_single(self, servo_id: int, position: int, duration: int = 500):
        """控制单个舵机"""
        pwm = max(PWM_MIN, min(PWM_MAX, int(position)))
        self._send(_cmd(servo_id, pwm, duration))
        time.sleep(duration / 1000 + 0.2)

    def stamp_at(self, position_values: dict):
        """在指定位置执行盖章：移动到目标位置 → 下压 → 抬起回中位"""
        neutral = {i: PWM_MID for i in range(6)}
        target = {i: int(position_values.get(i, PWM_MID)) for i in range(6)}

        self.move_to(target, 800)
        time.sleep(1.0)

        press = dict(target)
        press[3] = 1630
        self.move_to(press, 600)
        time.sleep(0.7)

        self.move_to(neutral, 800)
        time.sleep(1.0)

    def stamp_sequence(self):
        """执行默认盖章动作序列（固定位置）"""
        pos = {0: 1500, 1: 920, 2: 1655, 3: 1500, 4: 1500, 5: 1500}
        self.stamp_at(pos)

    def ping(self) -> bool:
        if SIMULATION_MODE:
            return True
        try:
            return self._ser is not None and self._ser.is_open
        except Exception:
            return False

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()
        WeArmController._ser = None

    def __del__(self):
        self.close()
