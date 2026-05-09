import cv2
import numpy as np
import time
import threading
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.deps import get_session
from vision.camera import SharedCamera
from config import CAMERA_INDEX, CAMERA_BACKEND, CAMERA_PROBE, CAMERA_BACKENDS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cameras", tags=["cameras"])

_camera_lock = threading.Lock()
_current_index = CAMERA_INDEX
_current_backend = CAMERA_BACKEND


class SelectRequest(BaseModel):
    index: int


@router.get("")
def list_cameras(session: dict = Depends(get_session)):
    """列出可用摄像头，使用启动时缓存的探测数据，不再重复打开摄像头。"""
    cameras = [
        {"index": i, "resolution": res}
        for i, res in sorted(CAMERA_PROBE.items())
    ]
    return {"cameras": cameras, "current": _current_index}


@router.post("/select")
def select_camera(body: SelectRequest, session: dict = Depends(get_session)):
    global _current_index, _current_backend
    with _camera_lock:
        old_index = _current_index
        old_backend = _current_backend
        try:
            # 使用探测阶段为该摄像头测出的最佳后端
            be = CAMERA_BACKENDS.get(body.index, cv2.CAP_MSMF)
            SharedCamera.get_instance().switch(body.index, backend=be)
            _current_index = body.index
            _current_backend = be
        except Exception as e:
            logger.error(f"切换摄像头失败: {e}")
            try:
                SharedCamera.get_instance().switch(old_index, backend=_current_backend)
            except Exception:
                pass
            return {"status": "error", "message": str(e)}
    return {"status": "ok", "index": body.index}


def _gen_frames():
    try:
        cam = SharedCamera.get_instance(index=_current_index, backend=_current_backend)
    except Exception as e:
        logger.error(f"摄像头初始化失败: {e}")
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, f"Camera Error: {e}", (20, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        _, buf = cv2.imencode(".jpg", frame)
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
        return

    black_count = 0
    try:
        while True:
            frame = cam.get_frame()
            if frame is None:
                time.sleep(0.03)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = float(np.mean(gray))
            if mean_brightness < 5:
                black_count += 1
            else:
                black_count = 0
            if black_count > 30:
                cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 180), -1)
                cv2.putText(frame, "Camera: No valid signal", (30, frame.shape[0] // 2 - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
                cv2.putText(frame, "Check connection or try another camera", (30, frame.shape[0] // 2 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
            _, buf = cv2.imencode(".jpg", frame)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
    except Exception:
        time.sleep(1)


# 视频流不需要登录验证（img 标签无法带 cookie）
@router.get("/video_feed")
def video_feed():
    return StreamingResponse(
        _gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
