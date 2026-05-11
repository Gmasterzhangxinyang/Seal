import cv2
import logging
import os
import threading
import time
from datetime import datetime
from config import CAMERA_INDEX, CAMERA_BACKEND, AUDIT_IMAGE_DIR

logger = logging.getLogger(__name__)

# 目标分辨率（文档扫描用 1280x720 更好，景深大不容易糊）
_TARGET_W, _TARGET_H = 1280, 720
# 支持的四字符编码格式（优先 MJPG，USB 摄像头高分辨率通常需要）
_FOURCC_OPTIONS = [
    cv2.VideoWriter_fourcc(*'MJPG'),
    cv2.VideoWriter_fourcc(*'YUY2'),
]


def _set_exposure(cap, for_external=False):
    """设置曝光/白平衡/自动对焦并记录结果。外部摄像头用手动曝光+更高增益。"""
    results = {}
    if for_external:
        # 外部摄像头：禁用自动曝光，手动拉高亮度
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # manual mode
        cap.set(cv2.CAP_PROP_EXPOSURE, 80)           # 拉高曝光
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 140)        # 拉高亮度
    else:
        for prop, val, name in [
            (cv2.CAP_PROP_AUTO_EXPOSURE, 1, 'AUTO_EXPOSURE'),
            (cv2.CAP_PROP_AUTO_WB, 1, 'AUTO_WB'),
            (cv2.CAP_PROP_AUTOFOCUS, 1, 'AUTOFOCUS'),
        ]:
            ok = cap.set(prop, val)
            results[name] = ok
            if not ok:
                logger.warning(f'cap.set({name}, {val}) 返回 False，摄像头可能不支持')
    mode = 'manual' if not results else str(results)
    logger.info('曝光设置结果: %s', mode)


def _try_open(index, backend, retries, retry_delay):
    """尝试用指定后端打开摄像头，返回 (cap, w, h) 或 (None, 0, 0)。"""
    for attempt in range(1, retries + 1):
        cap = cv2.VideoCapture(index, backend) if backend else cv2.VideoCapture(index)
        if not cap.isOpened():
            logger.warning(f'摄像头打开失败 backend={backend} (尝试 {attempt}/{retries})')
            if attempt < retries:
                time.sleep(retry_delay)
            continue

        best_w, best_h = 0, 0
        for fourcc in _FOURCC_OPTIONS:
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, _TARGET_W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, _TARGET_H)
            for _ in range(3):
                cap.grab()
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if w * h > best_w * best_h:
                best_w, best_h = w, h
            if w >= _TARGET_W and h >= _TARGET_H:
                break

        # 验证能读到帧（MSMF 有时 open 成功但 grab 失败）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, best_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, best_h)
        _set_exposure(cap)
        ret, _ = cap.read()
        if not ret:
            logger.warning(f'摄像头 index={index} backend={backend} 无法读帧，尝试其他后端')
            cap.release()
            continue

        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        logger.info(f'摄像头已打开: index={index}, backend={backend}, 分辨率={best_w}x{best_h}')
        return cap, best_w, best_h

    return None, 0, 0


def open_camera(index, retries=3, retry_delay=1.0, backend=None):
    """打开摄像头，优先使用指定后端，失败时自动回退。"""
    # 指定后端优先，回退到另一个
    backends = [backend] if backend else [None]
    if backend == cv2.CAP_MSMF:
        backends.append(cv2.CAP_DSHOW)
    elif backend == cv2.CAP_DSHOW:
        backends.append(cv2.CAP_MSMF)

    for be in backends:
        cap, w, h = _try_open(index, be, retries, retry_delay)
        if cap is not None:
            return cap

    logger.error(f'所有后端均无法打开摄像头 index={index}')
    return None


class SharedCamera:
    """单例摄像头 + 后台线程帧缓冲，避免多 VideoCapture 冲突"""
    _instance = None

    def __init__(self, index=0, backend=None):
        self._index = index
        self._backend = backend
        self._cap = open_camera(index, backend=backend)
        if self._cap is None:
            raise RuntimeError(f'无法打开摄像头（index={index}），请检查连接')
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._running = True
        self._error_count = 0
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        # 预热：等待若干帧让摄像头稳定
        self._warmup()
        w, h = self.get_resolution()
        logger.info(f'摄像头已启动: index={index}, 分辨率={w}x{h}')

    def _warmup(self, frames=60, timeout=8.0):
        """预热摄像头，丢弃前几帧以获得稳定图像。"""
        deadline = time.time() + timeout
        count = 0
        while count < frames and time.time() < deadline:
            ret, _ = self._cap.read()
            if ret:
                count += 1
            else:
                time.sleep(0.05)
        # 等待后台线程获取至少一帧
        while self._latest_frame is None and time.time() < deadline:
            time.sleep(0.05)

    def _read_loop(self):
        while self._running:
            try:
                ret, frame = self._cap.read()
                if ret:
                    with self._frame_lock:
                        self._latest_frame = frame
                    self._error_count = 0
                else:
                    self._error_count += 1
                    if self._error_count > 30:
                        logger.error('摄像头连续读取失败，等待重新初始化')
                        self._reconnect()
                        return  # 旧线程退出，新线程已由 _reconnect 创建
                    else:
                        time.sleep(0.01)
            except Exception as e:
                logger.warning(f'摄像头读取异常: {e}')
                time.sleep(1)

    def _reconnect(self):
        """摄像头断连后自动重连。"""
        self._running = False
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)
        try:
            self._cap.release()
        except Exception:
            pass
        time.sleep(1.0)
        try:
            cap = open_camera(self._index, retries=3, backend=self._backend)
            if cap is not None:
                self._cap = cap
                self._error_count = 0
                self._running = True
                self._thread = threading.Thread(target=self._read_loop, daemon=True)
                self._thread.start()
                self._warmup()
                logger.info('摄像头重连成功')
            else:
                logger.error('摄像头重连失败')
        except Exception as e:
            logger.error(f'摄像头重连异常: {e}')

    def get_frame(self):
        """返回最新帧副本（给视频流用）"""
        with self._frame_lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
        return None

    def capture(self, filename: str) -> str:
        """从帧缓冲取当前帧保存到文件"""
        with self._frame_lock:
            if self._latest_frame is not None:
                frame = self._latest_frame.copy()
            else:
                raise RuntimeError('摄像头尚未就绪，无可用帧')
        os.makedirs(AUDIT_IMAGE_DIR, exist_ok=True)
        path = os.path.join(AUDIT_IMAGE_DIR, filename)
        cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        logger.info(f'已保存图片: {path}')
        return path

    def capture_timestamped(self, tag: str) -> str:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        return self.capture(f'{ts}_{tag}.jpg')

    def get_resolution(self) -> tuple:
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return w, h

    def is_healthy(self) -> bool:
        """检查摄像头是否正常工作。"""
        return self._latest_frame is not None and self._error_count < 10

    def switch(self, index: int, backend=None):
        """在运行中切换到另一个摄像头，保持流连接不断。"""
        new_cap = open_camera(index, backend=backend or self._backend)
        if new_cap is None:
            raise RuntimeError(f'无法打开摄像头（index={index}）')
        # 新摄像头打开成功，替换旧的
        self._running = False
        self._thread.join(timeout=5)
        try:
            self._cap.release()
        except Exception:
            pass
        self._index = index
        self._backend = backend or self._backend
        self._cap = new_cap
        self._latest_frame = None
        self._error_count = 0
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        self._warmup()
        w, h = self.get_resolution()
        logger.info(f'摄像头已切换: index={index}, 分辨率={w}x{h}')

    @classmethod
    def get_instance(cls, index=None, backend=None):
        if cls._instance is None:
            idx = index if index is not None else CAMERA_INDEX
            be = backend if backend is not None else CAMERA_BACKEND
            cls._instance = cls(idx, backend=be)
        return cls._instance

    @classmethod
    def reset(cls):
        if cls._instance is not None:
            cls._instance._running = False
            try:
                cls._instance._cap.release()
            except Exception:
                pass
            cls._instance = None
