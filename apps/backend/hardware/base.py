import os
import json
import logging

logger = logging.getLogger(__name__)

CALIBRATION_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "calibration.json"
)


def load_calibration() -> dict:
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_calibration(data: dict):
    with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compute_position_at_xy(x: float, y: float, cal: dict | None = None) -> dict:
    """双线性插值：根据四角标定数据计算 (x, y) 处的位置值。"""
    if cal is None:
        cal = load_calibration()

    corners = cal.get("corners")
    if not corners or len(corners) < 4:
        raise RuntimeError("未完成四角标定")

    tl = corners["TL"]
    tr = corners["TR"]
    bl = corners["BL"]
    br = corners["BR"]

    result = {}
    for sid in range(6):
        if sid in (1, 3):
            continue
        top = tl[str(sid)] * (1 - x) + tr[str(sid)] * x
        bottom = bl[str(sid)] * (1 - x) + br[str(sid)] * x
        result[sid] = int(top * (1 - y) + bottom * y)

    return result
