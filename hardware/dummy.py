import logging
from hardware.base import ArmBase

logger = logging.getLogger(__name__)


class DummyArmController(ArmBase):
    """无硬件时的仿真控制器，所有操作只记日志不执行。"""

    def move_to(self, positions: dict, duration: int = 1000):
        logger.info(f'[仿真] move_to: {positions}')

    def move_single(self, servo_id: int, position: int, duration: int = 500):
        logger.info(f'[仿真] move_single: servo={servo_id}, pos={position}')

    def stamp_at(self, position_values: dict):
        logger.info(f'[仿真] stamp_at: {position_values}')

    def ping(self) -> bool:
        return True

    def close(self):
        pass

    @property
    def neutral_value(self) -> int:
        return 1500

    @property
    def value_min(self) -> int:
        return 500

    @property
    def value_max(self) -> int:
        return 2500
