import struct
import time
import logging
from config import SERIAL_PORT, SIMULATION_MODE
from hardware.base import ArmBase

logger = logging.getLogger(__name__)

# Hiwonder 总线舵机协议常量
_HEADER = bytes([0x55, 0x55])
_CMD_SERVO_MOVE = 0x03
_BAUD = 9600

# 位置值范围: 0-1000（对应 0°-240°）
_VALUE_MIN = 0
_VALUE_MAX = 1000
_VALUE_MID = 500

# 盖章相关位置值
# 中位=500，抬起=500，下压≈833（映射自 WeArm 2000）
STAMP_DOWN_POS = 833
STAMP_UP_POS = 500
STAMP_WRIST_POS = 333
WRIST_NEUTRAL_POS = 500


def _build_servo_move_cmd(servo_positions: dict, duration: int) -> bytes:
    """
    构建 Hiwonder 总线舵机移动指令。
    帧格式: 55 55 <length> 03 <num_servos> <time_low> <time_high> [<servo_id> <pos_low> <pos_high> ...]
    """
    servo_count = len(servo_positions)
    params = struct.pack('<B', servo_count)
    params += struct.pack('<H', duration)
    for sid, pos in servo_positions.items():
        params += struct.pack('<B', sid)
        params += struct.pack('<H', int(pos))

    length = 2 + len(params)  # command(1) + params
    return _HEADER + struct.pack('<B', length) + struct.pack('<B', _CMD_SERVO_MOVE) + params


class HiwonderArmController(ArmBase):
    """Hiwonder ArmPi 机械臂控制器（总线舵机协议，9600 波特率）"""

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
            logger.info('[仿真模式] HiwonderArmController 已初始化')

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
            self._ser = serial.Serial(SERIAL_PORT, _BAUD, timeout=3)
            time.sleep(2)
            self.move_to({i: _VALUE_MID for i in range(1, 7)}, 1000)
            time.sleep(1.5)
            logger.info(f'Hiwonder ArmPi 已连接: {SERIAL_PORT}')
        except Exception as e:
            raise RuntimeError(
                f'无法连接 Hiwonder ArmPi（{SERIAL_PORT}）：{e}\n'
                '请检查：1) USB线是否插好  2) 电源开关是否打开  3) 驱动是否安装'
            )

    def _send(self, data: bytes):
        if SIMULATION_MODE:
            logger.info(f'[仿真] 发送: {data.hex(" ")}')
            return
        if self._ser and self._ser.is_open:
            self._ser.write(data)

    def move_to(self, positions: dict, duration: int = 1000):
        """移动多舵机。positions: {servo_id(1-6): position(0-1000)}"""
        clamped = {}
        for sid, pos in positions.items():
            clamped[sid] = max(_VALUE_MIN, min(_VALUE_MAX, int(pos)))
        cmd = _build_servo_move_cmd(clamped, duration)
        self._send(cmd)
        time.sleep(duration / 1000 + 0.3)

    def move_single(self, servo_id: int, position: int, duration: int = 500):
        """控制单个舵机"""
        pos = max(_VALUE_MIN, min(_VALUE_MAX, int(position)))
        cmd = _build_servo_move_cmd({servo_id: pos}, duration)
        self._send(cmd)
        time.sleep(duration / 1000 + 0.2)

    def stamp_at(self, position_values: dict):
        """在指定位置执行盖章。position_values 包含各关节位置值(0-1000)。"""
        MOVE_TIME = 1200
        HOLD_TIME = 0.9
        LIFT_TIME = 1000

        # 移动到目标位置上方（S2 保持抬起，S4 调整角度）
        # 注意: Hiwonder 舵机 ID 从 1 开始
        move_pos = dict(position_values)
        move_pos[2] = STAMP_UP_POS
        move_pos[4] = STAMP_WRIST_POS
        self.move_to(move_pos, MOVE_TIME)

        # S2 下压盖章
        stamp_pos = dict(move_pos)
        stamp_pos[2] = STAMP_DOWN_POS
        self.move_to(stamp_pos, MOVE_TIME)
        time.sleep(HOLD_TIME)

        # 抬起
        reset_pos = dict(move_pos)
        reset_pos[2] = STAMP_UP_POS
        reset_pos[4] = WRIST_NEUTRAL_POS
        self.move_to(reset_pos, LIFT_TIME)

        # 回安全位置
        self.move_to({i: _VALUE_MID for i in range(1, 7)}, 1000)

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
        HiwonderArmController._ser = None

    def __del__(self):
        self.close()
