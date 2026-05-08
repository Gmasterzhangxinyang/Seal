"""
机械臂工厂模块 — 根据 config.ARM_TYPE 创建对应的控制器实例。
同时导出标定相关工具函数，保持向后兼容。
"""
import logging
from config import ARM_TYPE
from hardware.base import ArmBase, load_calibration, save_calibration, compute_position_at_xy

logger = logging.getLogger(__name__)


def create_controller() -> ArmBase:
    """根据配置创建机械臂控制器。连接失败时回退到仿真模式。"""
    try:
        if ARM_TYPE == 'hiwonder':
            from hardware.hiwonder import HiwonderArmController
            logger.info(f'创建 HiwonderArmController (ARM_TYPE={ARM_TYPE})')
            return HiwonderArmController()
        else:
            from hardware.wearm import WeArmController
            logger.info(f'创建 WeArmController (ARM_TYPE={ARM_TYPE})')
            return WeArmController()
    except Exception as e:
        logger.warning(f'机械臂连接失败，使用仿真模式: {e}')
        from hardware.dummy import DummyArmController
        return DummyArmController()


# 向后兼容导出
load_calibration
save_calibration
compute_position_at_xy
