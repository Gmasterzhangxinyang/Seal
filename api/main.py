import os
import sys
import logging
import traceback
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ─── 日志配置 ──────────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'log')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, datetime.now().strftime('%y%m%d_%H%M%S') + '.log')

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)-8s %(name)s: %(message)s'
))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)
logger.info(f'日志文件: {LOG_FILE}')


def _global_exception_hook(exc_type, exc_value, exc_tb):
    """捕获未处理异常写入日志"""
    logger.critical(
        '未捕获异常:\n' + ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    )


sys.excepthook = _global_exception_hook

# ─── FastAPI 应用 ─────────────────────────────────────────────────────────────
from database.models import init_db
from database.seed import seed_demo_data, seed_default_templates
from config import WEB_HOST, WEB_PORT, BASE_DIR

app = FastAPI(title="文档盖章机器人", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from api.auth import router as auth_router
from api.cameras import router as cameras_router
from api.stamp import router as stamp_router
from api.logs import router as logs_router
from api.review import router as review_router
from api.templates import router as templates_router
from api.stats import router as stats_router
from api.calibration import router as calibration_router
from api.images import router as images_router
from api.users import router as users_router

app.include_router(auth_router, prefix="/api")
app.include_router(cameras_router, prefix="/api")
app.include_router(stamp_router, prefix="/api")
app.include_router(logs_router, prefix="/api")
app.include_router(review_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(calibration_router, prefix="/api")
app.include_router(images_router, prefix="/api")
app.include_router(users_router, prefix="/api")

# 生产环境：服务前端静态文件
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    from starlette.responses import FileResponse as StarletteFileResponse

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = os.path.join(FRONTEND_DIST, path)
        if path and os.path.isfile(file_path):
            return StarletteFileResponse(file_path)
        return StarletteFileResponse(os.path.join(FRONTEND_DIST, "index.html"))


def start():
    import uvicorn
    init_db()
    seed_demo_data()
    seed_default_templates()
    # 预初始化摄像头（config.py 自动检测时已缓存 CAMERA_PROBE）
    try:
        from vision.camera import SharedCamera
        from config import CAMERA_INDEX, CAMERA_BACKEND
        SharedCamera.get_instance(index=CAMERA_INDEX, backend=CAMERA_BACKEND)
        logger.info('摄像头初始化完成')
    except Exception as e:
        logger.warning(f'摄像头初始化失败（后端仍可运行）: {e}')
    uvicorn.run(app, host=WEB_HOST, port=WEB_PORT)


if __name__ == "__main__":
    start()
