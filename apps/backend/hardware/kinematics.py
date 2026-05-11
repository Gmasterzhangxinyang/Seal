"""WeArm 逆运动学求解器。

从 STEP 图纸提取的连杆参数:
  H0 ≈ 20mm  (底座旋转轴 → 肩关节)
  L1 ≈ 103mm (肩关节 → 肘关节)
  L2 ≈ 96mm  (肘关节 → 腕关节)
  L3 ≈ 50mm  (腕关节 → 末端执行器/印章)

WeArm PWM 映射 (MG996R / DS3225 等标准舵机):
  500  → 0°
  1500 → 90°
  2500 → 180°
"""

import math
import logging

logger = logging.getLogger(__name__)

# ─── 连杆参数 (mm) ─────────────────────────────────────────────────────────
H0 = 20.0  # 底座旋转轴到肩关节的垂直距离
L1 = 103.0  # 大臂长度 (肩→肘)
L2 = 96.0  # 小臂长度 (肘→腕)
L3 = 50.0  # 腕到末端执行器 (可调，取决于印章安装方式)

# ─── WeArm PWM ↔ 角度转换 ──────────────────────────────────────────────────
PWM_MIN = 500
PWM_MAX = 2500
PWM_MID = 1500
# 舵机行程 0°~180°, PWM 500~2500
DEG_PER_PWM = 180.0 / (PWM_MAX - PWM_MIN)  # 0.09 °/PWM


def pwm_to_deg(pwm: int) -> float:
    return (pwm - PWM_MIN) * DEG_PER_PWM


def deg_to_pwm(deg: float) -> int:
    pwm = deg / DEG_PER_PWM + PWM_MIN
    return max(PWM_MIN, min(PWM_MAX, int(round(pwm))))


# ─── 各舵机安装偏移 (度) ────────────────────────────────────────────────────
# 实际安装中各舵机的零位偏移，需要通过标定调整。
# 这些值表示：当机械臂竖直向上时各舵机对应的 PWM 角度。
# 初始值基于 WeArm 默认安装姿态。
SERVO_OFFSETS = {
    0: 90.0,  # 底盘: 90° = 正前方
    1: 90.0,  # 大臂: 90° = 水平
    2: 90.0,  # 小臂: 90° = 与大臂同向
    3: 90.0,  # 手腕: 90° = 保持末端朝下
}


def inverse_kinematics(
    x: float,
    y: float,
    z: float,
    wrist_angle: float = -90.0,
    h0: float = H0,
    l1: float = L1,
    l2: float = L2,
    l3: float = L3,
) -> dict:
    """三自由度逆运动学求解。

    坐标系: 底座旋转轴为原点，Z 轴向上。
    机械臂在 YZ 平面内运动（底座旋转对齐 X 方向）。

    参数:
        x, y, z: 目标位置 (mm)
        wrist_angle: 末端执行器相对水平面的俯仰角 (度),
                     -90 = 竖直朝下 (盖章默认姿态)

    返回:
        {servo_id: pwm_value} 或 None (超出工作空间)
    """
    # 底座旋转角 (绕 Z 轴)
    if abs(x) < 0.01 and abs(y) < 0.01:
        theta0 = 0.0
    else:
        theta0 = math.atan2(y, x)

    # 在臂平面内，将目标转换到 2D (r, h)
    r = math.sqrt(x**2 + y**2)  # 水平距离

    # 考虑 L3 和手腕角度偏移
    # 末端朝下时 (wrist_angle = -90°)，腕关节位于目标正上方 L3 处
    wr = math.radians(wrist_angle)
    wrist_x = r - l3 * math.cos(wr)
    wrist_z = (z - h0) - l3 * math.sin(wr)

    # 肩关节到腕关节的距离
    d_sq = wrist_x**2 + wrist_z**2
    d = math.sqrt(d_sq)

    # 可达性检查
    if d > l1 + l2 - 0.1:
        logger.warning(f"目标超出工作空间: d={d:.1f} > L1+L2={l1 + l2:.1f}")
        return None
    if d < abs(l1 - l2) + 0.1:
        logger.warning(f"目标过近: d={d:.1f} < |L1-L2|={abs(l1 - l2):.1f}")
        return None

    # 肘关节角 (余弦定理)
    cos_elbow = (d_sq - l1**2 - l2**2) / (2 * l1 * l2)
    cos_elbow = max(-1.0, min(1.0, cos_elbow))
    theta2 = math.acos(cos_elbow)  # 肘关节相对大臂的弯曲角

    # 肩关节角
    alpha = math.atan2(wrist_z, wrist_x)  # 肩到腕的方向角
    beta = math.acos((l1**2 + d_sq - l2**2) / (2 * l1 * d))  # 偏转角
    theta1 = alpha + beta  # 大臂相对水平面的仰角

    # 腕关节角 (保持末端朝下)
    theta3 = wr - theta1 - theta2  # 相对大臂的补偿角

    # 转换到舵机角度 (0°~180°)
    # 底盘: atan2 结果 [-π, π] → [0°, 180°]
    servo0_deg = math.degrees(theta0)
    if servo0_deg < 0:
        servo0_deg += 360.0
    # 映射到舵机 0°~180° 范围
    servo0_deg = max(0, min(180, servo0_deg))

    # 大臂: theta1 相对水平面，映射到舵机角度
    servo1_deg = 90.0 + math.degrees(theta1)
    servo1_deg = max(0, min(180, servo1_deg))

    # 小臂: theta2 是弯曲角，映射
    servo2_deg = math.degrees(theta2)
    servo2_deg = max(0, min(180, servo2_deg))

    # 手腕: 保持末端朝下
    servo3_deg = 90.0 + math.degrees(theta3)
    servo3_deg = max(0, min(180, servo3_deg))

    result = {
        0: deg_to_pwm(servo0_deg),
        1: deg_to_pwm(servo1_deg),
        2: deg_to_pwm(servo2_deg),
        3: deg_to_pwm(servo3_deg),
    }

    logger.info(
        f"IK: target=({x:.1f},{y:.1f},{z:.1f}) → "
        f"θ=({servo0_deg:.1f}°,{servo1_deg:.1f}°,{servo2_deg:.1f}°,{servo3_deg:.1f}°) "
        f"PWM={result}"
    )

    return result


def pixel_to_world(cx: float, cy: float, img_w: int, img_h: int, cal: dict) -> tuple:
    """将图像像素坐标转换为机械臂世界坐标。

    使用四角标定数据中的角点世界坐标进行双线性插值。

    参数:
        cx, cy: 目标在图像中的像素坐标
        img_w, img_h: 图像尺寸
        cal: 标定数据，包含 corners 和可选的 world_corners

    返回:
        (x, y, z) 世界坐标 (mm)，z 为工作面高度
    """
    corners = cal.get("corners")
    if not corners or len(corners) < 4:
        raise RuntimeError("未完成四角标定")

    # 归一化坐标
    nx = cx / img_w if img_w > 0 else 0.5
    ny = cy / img_h if img_h > 0 else 0.5

    # 检查是否有世界坐标标定
    world_corners = cal.get("world_corners")
    if world_corners and len(world_corners) == 4:
        # 使用标定的世界坐标进行插值
        tl = world_corners["TL"]
        tr = world_corners["TR"]
        bl = world_corners["BL"]
        br = world_corners["BR"]
    else:
        # 回退: 使用标定的 PWM 值 + IK 逆推
        # 通过 PWM 值推算世界坐标 (简化: 使用默认工作面)
        logger.info("未找到 world_corners，使用默认工作面坐标")

        # 简化估算: 工作面范围
        reach = L1 + L2 + L3
        x_min = reach * 0.3
        x_max = reach * 0.8
        y_offset = 0

        x = x_min + (x_max - x_min) * nx
        y = y_offset + (x_max - x_min) * (ny - 0.5) * 0.5
        z = 0  # 工作面高度
        return x, y, z

    # 双线性插值世界坐标
    top_x = tl[0] * (1 - nx) + tr[0] * nx
    top_y = tl[1] * (1 - nx) + tr[1] * nx
    bot_x = bl[0] * (1 - nx) + br[0] * nx
    bot_y = bl[1] * (1 - nx) + br[1] * nx

    x = top_x * (1 - ny) + bot_x * ny
    y = top_y * (1 - ny) + bot_y * ny
    z = 0  # 工作面高度

    return x, y, z


def compute_stamp_pwm(
    cx: float, cy: float, img_w: int, img_h: int, cal: dict
) -> dict | None:
    """完整的盖章坐标转换: 像素 → 世界坐标 → IK → PWM。

    参数:
        cx, cy: 盖章目标在图像中的像素坐标
        img_w, img_h: 图像尺寸
        cal: 标定数据

    返回:
        {servo_id: pwm} 或 None
    """
    try:
        x, y, z = pixel_to_world(cx, cy, img_w, img_h, cal)
        logger.info(f"像素({cx:.0f},{cy:.0f}) → 世界坐标({x:.1f},{y:.1f},{z:.1f})")
        return inverse_kinematics(x, y, z)
    except Exception as e:
        logger.error(f"盖章坐标转换失败: {e}")
        return None
