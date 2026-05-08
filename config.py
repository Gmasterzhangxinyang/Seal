import os
import logging
import time

# ─── 机械臂类型 ──────────────────────────────────────────────────────────────
# 'wearm'   — 老款 WeArm（PWM 文本协议，CH340，115200 波特率）
# 'hiwonder' — Hiwonder ArmPi（WiFi 网络连接，HTTP 控制）
ARM_TYPE = 'wearm'

# Hiwonder ArmPi 网络配置（WiFi AP 模式默认值）
HIWONDER_HOST = '192.168.1.175'  # 树莓派 IP
HIWONDER_PORT = 9999              # 中继服务端口

# ─── 串口配置（仅 WeArm 使用）────────────────────────────────────────────────
SERIAL_BAUD = 115200

def _auto_detect_serial_port() -> str:
    """自动检测 CH340 串口（WeArm 使用）"""
    if ARM_TYPE == 'hiwonder':
        return ''
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if 'CH340' in p.description or (p.vid == 0x1A86 and p.pid == 0x7523):
                logging.info(f'自动检测到 CH340 串口: {p.device} ({p.description})')
                return p.device
        for p in ports:
            if 'USB' in p.description.upper() or 'SERIAL' in p.description.upper():
                logging.info(f'回退匹配串口: {p.device} ({p.description})')
                return p.device
        logging.warning('未检测到 USB 串口设备')
    except ImportError:
        logging.warning('pyserial 未安装，串口自动检测不可用')
    except Exception as e:
        logging.warning(f'串口自动检测失败: {e}')
    return ''

SERIAL_PORT = _auto_detect_serial_port()


# ─── 摄像头 ──────────────────────────────────────────────────────────────────

def _auto_detect_camera() -> tuple:
    """自动检测摄像头，返回 (index, backend, probe_info)。

    策略：
    1. 遍历 index 0-4，用 DSHOW 后端打开
    2. 对每个摄像头读帧测亮度，选亮度最高的（跳过全黑的红外/深度摄像头）
    3. 同时缓存所有摄像头的分辨率信息，供 list_cameras 使用
    """
    import cv2
    import numpy as np

    best_idx, best_brightness = 0, -1
    for idx in range(5):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            continue
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        for _ in range(5):
            cap.grab()
        ret, frame = cap.read()
        # 缓存分辨率
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        CAMERA_PROBE[idx] = f"{w}x{h}"
        brightness = float(np.mean(frame)) if ret and frame is not None else 0
        cap.release()
        logging.info(f'DSHOW 摄像头 index={idx}: brightness={brightness:.0f}, resolution={w}x{h}')
        if brightness > 10 and brightness > best_brightness:
            best_idx, best_brightness = idx, brightness

    if best_brightness > 0:
        logging.info(f'自动选择摄像头: index={best_idx} (brightness={best_brightness:.0f})')
        return best_idx, cv2.CAP_DSHOW

    logging.warning('未检测到可用摄像头，使用默认 index=0')
    return 0, None

# 启动探测时缓存的摄像头分辨率 {index: "WxH"}
CAMERA_PROBE: dict[int, str] = {}
CAMERA_INDEX, CAMERA_BACKEND = _auto_detect_camera()

# ─── 路径 ────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
AUDIT_IMAGE_DIR = os.path.join(BASE_DIR, 'audit_images')
EXAMPLE_IMAGE_DIR = os.path.join(BASE_DIR, 'example_images')

# ─── 数据库（MySQL）─────────────────────────────────────────────────────────
DB_HOST     = 'localhost'
DB_PORT     = 3306
DB_USER     = 'stamp_robot'
DB_PASSWORD = 'stamp_robot_pwd'
DB_NAME     = 'stamp_robot'
DATABASE_URL = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'

# ─── Web ─────────────────────────────────────────────────────────────────────
SECRET_KEY = 'stamp_robot_mec202_secret'
WEB_HOST   = '0.0.0.0'
WEB_PORT   = 5001

# ─── 文档规则 ─────────────────────────────────────────────────────────────────
# 不同文件类型需要的必填字段
REQUIRED_FIELDS = {
    'leave':    ['姓名', '学号', '日期', '原因'],
    'expense':  ['姓名', '学号', '日期', '金额'],
    'cert':     ['姓名', '学号', '日期'],
    'general':  ['姓名', '日期'],
}

# 签名关键词（OCR扫到这些词说明有签名栏）
SIGNATURE_KEYWORDS = ['签名', '签字', '审批', '审核人', '负责人', '盖章']

# ─── 文档管理系统（DMS）集成 ──────────────────────────────────────────────────
# 如果学校没有DMS，设为空字符串即可，系统会跳过上传
DMS_BASE_URL = ''
DMS_API_KEY  = ''

# ─── 逆运动学参数 (WeArm, 从 STEP 图纸提取) ───────────────────────────────────
ARM_H0 = 20.0    # 底座旋转轴到肩关节的垂直距离 (mm)
ARM_L1 = 103.0   # 大臂长度 (mm)
ARM_L2 = 96.0    # 小臂长度 (mm)
ARM_L3 = 50.0    # 腕到末端执行器/印章的距离 (mm)

# ─── 硬件仿真模式 ─────────────────────────────────────────────────────────────
SIMULATION_MODE = False

# ─── 纸张检测 ─────────────────────────────────────────────────────────────────
# False = 跳过纸张检测，直接拍照识别（固定纸张位置时使用）
PAPER_DETECTION_ENABLED = False
