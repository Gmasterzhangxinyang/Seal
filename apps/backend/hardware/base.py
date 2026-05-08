import os
import json
import logging
from abc import ABC, abstractmethod
from config import BASE_DIR

logger = logging.getLogger(__name__)

CALIBRATION_FILE = os.path.join(BASE_DIR, 'calibration.json')


class ArmBase(ABC):
    """机械臂统一接口。WeArm 和 Hiwonder 均实现此接口。"""

    @abstractmethod
    def move_to(self, positions: dict, duration: int = 1000):
        """移动多舵机到指定位置。positions: {servo_id: position_value}"""
        ...

    @abstractmethod
    def move_single(self, servo_id: int, position: int, duration: int = 500):
        """控制单个舵机"""
        ...

    @abstractmethod
    def stamp_at(self, position_values: dict):
        """在指定位置执行盖章。position_values 包含各关节的位置值。"""
        ...

    @abstractmethod
    def ping(self) -> bool:
        """检测机械臂连接状态"""
        ...

    @abstractmethod
    def close(self):
        """关闭连接"""
        ...

    @property
    @abstractmethod
    def neutral_value(self) -> int:
        """中位值（WeArm=1500, Hiwonder=500）"""
        ...

    @property
    @abstractmethod
    def value_min(self) -> int:
        """最小值"""
        ...

    @property
    @abstractmethod
    def value_max(self) -> int:
        """最大值"""
        ...


def load_calibration() -> dict:
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_calibration(data: dict):
    with open(CALIBRATION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_position_at_xy(x: float, y: float, cal: dict | None = None) -> dict:
    """
    双线性插值：根据四角标定数据计算 (x, y) 处的位置值。
    x, y 为归一化坐标 (0~1)，(0,0)=左上角，(1,1)=右下角。
    """
    if cal is None:
        cal = load_calibration()

    corners = cal.get('corners')
    if not corners or len(corners) < 4:
        raise RuntimeError('未完成四角标定')

    tl = corners['top_left']
    tr = corners['top_right']
    bl = corners['bottom_left']
    br = corners['bottom_right']

    result = {}
    for sid in range(6):
        if sid in (1, 3):
            continue
        top = tl[str(sid)] * (1 - x) + tr[str(sid)] * x
        bottom = bl[str(sid)] * (1 - x) + br[str(sid)] * x
        result[sid] = int(top * (1 - y) + bottom * y)

    return result
