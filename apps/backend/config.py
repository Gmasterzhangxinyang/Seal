import os
import logging

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ─── 串口配置（WeArm）────────────────────────────────────────────────────────
SERIAL_BAUD = 115200


def _auto_detect_serial_port() -> str:
    """自动检测 CH340 串口（WeArm 使用）"""
    try:
        import serial.tools.list_ports

        ports = serial.tools.list_ports.comports()
        for p in ports:
            if "CH340" in p.description or (p.vid == 0x1A86 and p.pid == 0x7523):
                logging.info(f"自动检测到 CH340 串口: {p.device} ({p.description})")
                return p.device
        for p in ports:
            if "USB" in p.description.upper() or "SERIAL" in p.description.upper():
                logging.info(f"回退匹配串口: {p.device} ({p.description})")
                return p.device
        logging.warning("未检测到 USB 串口设备")
    except ImportError:
        logging.warning("pyserial 未安装，串口自动检测不可用")
    except Exception as e:
        logging.warning(f"串口自动检测失败: {e}")
    return ""


SERIAL_PORT = "COM10"


# ─── 摄像头 ──────────────────────────────────────────────────────────────────


def _probe_one_camera(idx, backend, backend_name):
    """用指定后端探测单个摄像头，返回 (ok, brightness, w, h)。"""
    import cv2
    import numpy as np

    try:
        cap = cv2.VideoCapture(idx, backend)
        if not cap.isOpened():
            return False, 0, 0, 0
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        cap.set(cv2.CAP_PROP_AUTO_WB, 1)
        for _ in range(15):
            cap.grab()
        ret, frame = cap.read()
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        brightness = float(np.mean(frame)) if ret and frame is not None else 0
        ok = ret and frame is not None and brightness > 10
        return ok, brightness, w, h
    except Exception as e:
        logging.warning(f"{backend_name} 探测 index={idx} 异常: {e}")
        return False, 0, 0, 0


def _auto_detect_camera() -> tuple:
    """自动检测摄像头，返回 (index, backend)。

    策略：
    1. 遍历 index 0-4，对每个摄像头分别测试 MSMF 和 DSHOW 后端
    2. MSMF 对内置摄像头自动曝光支持更好，DSHOW 对部分 USB 摄像头兼容性更好
    3. 选亮度最高的摄像头，记录每个摄像头适用的后端
    """
    import cv2

    best_idx, best_brightness, best_backend = 0, -1, cv2.CAP_MSMF

    for idx in range(5):
        chosen_backend = None
        chosen_res = "0x0"

        # 优先尝试 MSMF
        ok, brightness, w, h = _probe_one_camera(idx, cv2.CAP_MSMF, "MSMF")
        if ok:
            logging.info(
                f"MSMF 摄像头 index={idx}: OK, brightness={brightness:.0f}, resolution={w}x{h}"
            )
            chosen_backend = cv2.CAP_MSMF
            chosen_res = f"{w}x{h}"
        else:
            # MSMF 失败，回退 DSHOW
            ok2, brightness, w, h = _probe_one_camera(idx, cv2.CAP_DSHOW, "DSHOW")
            if ok2:
                logging.info(
                    f"DSHOW 摄像头 index={idx}: OK, brightness={brightness:.0f}, resolution={w}x{h}"
                )
                chosen_backend = cv2.CAP_DSHOW
                chosen_res = f"{w}x{h}"
            else:
                logging.info(f"摄像头 index={idx}: MSMF/DSHOW 均不可用")
                continue

        CAMERA_PROBE[idx] = chosen_res
        CAMERA_BACKENDS[idx] = chosen_backend

        if brightness > best_brightness:
            best_idx, best_brightness, best_backend = idx, brightness, chosen_backend

    if best_brightness > 0:
        logging.info(
            f"自动选择摄像头: index={best_idx}, backend={'MSMF' if best_backend == cv2.CAP_MSMF else 'DSHOW'} (brightness={best_brightness:.0f})"
        )
        return best_idx, best_backend

    logging.warning("未检测到可用摄像头，使用默认 index=0")
    return 0, cv2.CAP_MSMF


# 启动探测时缓存的摄像头分辨率 {index: "WxH"}
CAMERA_PROBE: dict[int, str] = {}
# 每个摄像头适用的后端 {index: cv2.CAP_MSMF / cv2.CAP_DSHOW}
CAMERA_BACKENDS: dict[int, int] = {}
CAMERA_INDEX, CAMERA_BACKEND = _auto_detect_camera()

# ─── 路径 ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_IMAGE_DIR = os.path.join(BASE_DIR, "audit_images")
EXAMPLE_IMAGE_DIR = os.path.join(BASE_DIR, "example_images")

# ─── 数据库（MySQL）─────────────────────────────────────────────────────────
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "stamp_robot")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "stamp_robot")
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# ─── Web ─────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-fallback-key")
WEB_HOST = "0.0.0.0"
WEB_PORT = 5001

# ─── 文档规则 ─────────────────────────────────────────────────────────────────
# 不同文件类型需要的必填字段
REQUIRED_FIELDS = {
    "leave": ["姓名", "学号", "日期", "原因"],
    "expense": ["姓名", "学号", "日期", "金额"],
    "cert": ["姓名", "学号", "日期"],
    "general": ["姓名", "日期"],
}

# 签名关键词（OCR扫到这些词说明有签名栏）
SIGNATURE_KEYWORDS = ["签名", "签字", "审批", "审核人", "负责人", "盖章"]

# ─── 文档管理系统（DMS）集成 ──────────────────────────────────────────────────
# 如果学校没有DMS，设为空字符串即可，系统会跳过上传
DMS_BASE_URL = os.environ.get("DMS_BASE_URL", "")
DMS_API_KEY = os.environ.get("DMS_API_KEY", "")

# ─── 硬件仿真模式 ─────────────────────────────────────────────────────────────
SIMULATION_MODE = False

# ─── 纸张检测 ─────────────────────────────────────────────────────────────────
PAPER_DETECTION_ENABLED = True

# ─── OpenAI Vision ──────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
VLM_API_KEY = os.environ.get("ZHIPU_API_KEY", "")  # 智谱 key 用于 VLM
VLM_BASE_URL = os.environ.get("VLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
VLM_MODEL = os.environ.get("VLM_MODEL", "glm-4.6v")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "glm-4-flash")

# ─── Fish Audio TTS ────────────────────────────────────────────────────────────
FISH_AUDIO_API_KEY = os.environ.get("FISH_AUDIO_API_KEY", "")

# ─── DashScope ASR ────────────────────────────────────────────────────────────
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

# ─── Dify AI 审批 ──────────────────────────────────────────────────────────────
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "app-YLvNXsCxer7Q5VKS0bsjdmit")
