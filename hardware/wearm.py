import time
import logging
from config import SERIAL_PORT, SERIAL_BAUD, SIMULATION_MODE
from hardware.base import ArmBase

logger = logging.getLogger(__name__)

# WeArm 舵机名称映射
SERVO_NAMES = {0: '底盘', 1: '大臂', 2: '小臂', 3: '手腕', 4: '夹爪', 5: '辅助'}

# WeArm PWM 值范围
_VALUE_MIN = 500
_VALUE_MAX = 2500
_VALUE_MID = 1500

# 盖章相关 PWM 值
STAMP_DOWN_PWM = 2000
STAMP_UP_PWM = 1500
STAMP_WRIST_PWM = 1300
WRIST_NEUTRAL_PWM = 1500


def _cmd(servo_id: int, pwm: int, duration: int) -> bytes:
    return f'#{servo_id:03d}P{pwm:04d}T{duration:04d}!'.encode()


def _cmd_multi(*cmds) -> bytes:
    body = ''.join(f'#{i:03d}P{p:04d}T{t:04d}!' for i, p, t in cmds)
    return f'{{{body}}}'.encode()


class WeArmController(ArmBase):
    """老款 WeArm 机械臂控制器（PWM 文本协议，CH340，115200 波特率）"""

    _instance = None
    _ser = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not SIMULATION_MODE and self._ser is None:
            self._connect()
        elif SIMULATION_MODE:
            logger.info('[仿真模式] WeArmController 已初始化')

    @property
    def neutral_value(self) -> int:
        return _VALUE_MID

    @property
    def value_min(self) -> int:
        return _VALUE_MIN

    @property
    def value_max(self) -> int:
        return _VALUE_MAX

    def _connect(self):
        import serial
        try:
            self._ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=3)
            time.sleep(2)
            self._send(_cmd_multi(
                (0, _VALUE_MID, 1000), (1, _VALUE_MID, 1000), (2, _VALUE_MID, 1000),
                (3, _VALUE_MID, 1000), (4, _VALUE_MID, 1000), (5, _VALUE_MID, 1000),
            ))
            time.sleep(1.5)
            logger.info(f'WeArm 已连接: {SERIAL_PORT}')
        except Exception as e:
            raise RuntimeError(
                f'无法连接 WeArm（{SERIAL_PORT}）：{e}\n'
                '请检查：1) USB线是否插好  2) 电源开关是否打开  3) CH340驱动是否安装'
            )

    def _send(self, data: bytes):
        if SIMULATION_MODE:
            logger.info(f'[仿真] 发送: {data.decode()!r}')
            return
        if self._ser and self._ser.is_open:
            self._ser.write(data)

    def move_to(self, positions: dict, duration: int = 1000):
        """移动到指定 PWM 位置。positions: {servo_id: pwm_value}"""
        cmds = tuple((sid, int(pwm), duration) for sid, pwm in positions.items())
        self._send(_cmd_multi(*cmds))
        time.sleep(duration / 1000 + 0.3)

    def move_single(self, servo_id: int, position: int, duration: int = 500):
        """控制单个舵机"""
        pwm = max(_VALUE_MIN, min(_VALUE_MAX, int(position)))
        self._send(_cmd(servo_id, pwm, duration))
        time.sleep(duration / 1000 + 0.2)

    def stamp_at(self, position_values: dict):
        """在指定位置执行盖章。position_values 包含 S0/S2 等定位关节的 PWM。"""
        MOVE_TIME = 1200
        HOLD_TIME = 0.9
        LIFT_TIME = 1000

        # 移动到目标位置上方（S1 保持抬起，S3 调整角度）
        move_pwms = dict(position_values)
        move_pwms[1] = STAMP_UP_PWM
        move_pwms[3] = STAMP_WRIST_PWM
        self.move_to(move_pwms, MOVE_TIME)

        # S1 下压盖章
        stamp_pwms = dict(move_pwms)
        stamp_pwms[1] = STAMP_DOWN_PWM
        self.move_to(stamp_pwms, MOVE_TIME)
        time.sleep(HOLD_TIME)

        # 抬起
        reset_pwms = dict(move_pwms)
        reset_pwms[1] = STAMP_UP_PWM
        reset_pwms[3] = WRIST_NEUTRAL_PWM
        self.move_to(reset_pwms, LIFT_TIME)

        # 回安全位置
        self.move_to({i: _VALUE_MID for i in range(6)}, 1000)

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
