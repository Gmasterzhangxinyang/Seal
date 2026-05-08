import time
import logging
import requests as http_client
from config import SIMULATION_MODE, HIWONDER_HOST, HIWONDER_PORT
from hardware.base import ArmBase

logger = logging.getLogger(__name__)

_BASE_URL = f'http://{HIWONDER_HOST}:{HIWONDER_PORT}'

# Hiwonder 总线舵机位置值范围: 0-1000（对应 0°-240°）
_VALUE_MIN = 0
_VALUE_MAX = 1000
_VALUE_MID = 500

# 盖章相关位置值
STAMP_DOWN_POS = 833
STAMP_UP_POS = 500
STAMP_WRIST_POS = 333
WRIST_NEUTRAL_POS = 500


class HiwonderArmController(ArmBase):
    """Hiwonder ArmPi 机械臂控制器（通过 WiFi + HTTP 与树莓派中继服务通信）"""

    def __init__(self):
        if not SIMULATION_MODE:
            self._check_connection()
        else:
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

    def _check_connection(self):
        try:
            resp = http_client.get(f'{_BASE_URL}/ping', timeout=3)
            resp.raise_for_status()
            logger.info(f'Hiwonder ArmPi 已连接: {HIWONDER_HOST}:{HIWONDER_PORT}')
        except Exception as e:
            raise RuntimeError(
                f'无法连接 Hiwonder ArmPi（{HIWONDER_HOST}:{HIWONDER_PORT}）：{e}\n'
                '请检查：1) WiFi 是否连接到 HW 开头的热点  '
                '2) 树莓派是否已开机  3) 中继服务是否已启动（python hiwonder_server.py）'
            )

    def _send_move(self, positions: dict, duration: int):
        """发送舵机移动指令到树莓派中继服务。"""
        if SIMULATION_MODE:
            logger.info(f'[仿真] move_to: {positions}, duration={duration}')
            return
        http_client.post(f'{_BASE_URL}/servo/move', json={
            'positions': {str(k): v for k, v in positions.items()},
            'duration': duration,
        }, timeout=10)

    def move_to(self, positions: dict, duration: int = 1000):
        """移动多舵机。positions: {servo_id(1-6): position(0-1000)}"""
        clamped = {k: max(_VALUE_MIN, min(_VALUE_MAX, int(v))) for k, v in positions.items()}
        self._send_move(clamped, duration)
        time.sleep(duration / 1000 + 0.3)

    def move_single(self, servo_id: int, position: int, duration: int = 500):
        """控制单个舵机"""
        pos = max(_VALUE_MIN, min(_VALUE_MAX, int(position)))
        self._send_move({servo_id: pos}, duration)
        time.sleep(duration / 1000 + 0.2)

    def stamp_at(self, position_values: dict):
        """在指定位置执行盖章。position_values 包含各关节位置值(0-1000)。"""
        MOVE_TIME = 1200
        HOLD_TIME = 0.9
        LIFT_TIME = 1000

        move_pos = dict(position_values)
        move_pos[2] = STAMP_UP_POS
        move_pos[4] = STAMP_WRIST_POS
        self.move_to(move_pos, MOVE_TIME)

        stamp_pos = dict(move_pos)
        stamp_pos[2] = STAMP_DOWN_POS
        self.move_to(stamp_pos, MOVE_TIME)
        time.sleep(HOLD_TIME)

        reset_pos = dict(move_pos)
        reset_pos[2] = STAMP_UP_POS
        reset_pos[4] = WRIST_NEUTRAL_POS
        self.move_to(reset_pos, LIFT_TIME)

        self.move_to({i: _VALUE_MID for i in range(1, 7)}, 1000)

    def ping(self) -> bool:
        if SIMULATION_MODE:
            return True
        try:
            resp = http_client.get(f'{_BASE_URL}/ping', timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def close(self):
        try:
            if not SIMULATION_MODE:
                self.move_to({i: _VALUE_MID for i in range(1, 7)}, 1000)
        except Exception as e:
            logger.warning(f'HiwonderArmController close 时出错: {e}')

    def __del__(self):
        self.close()
