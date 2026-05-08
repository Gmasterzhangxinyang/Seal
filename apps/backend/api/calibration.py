import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_session, require_role
from hardware.arm import load_calibration, save_calibration, create_controller
from config import ARM_TYPE

router = APIRouter(prefix="/calibration", tags=["calibration"])

_arm = None


def get_arm():
    global _arm
    if _arm is None:
        _arm = create_controller()
    return _arm


@router.get("/load")
def cal_load(session: dict = Depends(get_session)):
    return load_calibration()


@router.post("/ping")
def cal_ping(session: dict = Depends(require_role("admin"))):
    try:
        arm = get_arm()
        mid = arm.neutral_value
        arm.move_to({i: mid for i in range(6)}, 1000)
        ok = arm.ping()
        logging.info(f"[标定] ping: connected={ok}")
        return {"status": "ok", "connected": ok}
    except Exception as e:
        logging.error(f"[标定] ping 失败: {e}")
        return {"status": "error", "message": str(e)}


class MoveSingleRequest(BaseModel):
    servo_id: int
    pwm: int
    duration: int = 500


@router.post("/move_single")
def cal_move_single(body: MoveSingleRequest, session: dict = Depends(require_role("admin"))):
    try:
        logging.info(f"[标定] S{body.servo_id} -> PWM {body.pwm}")
        get_arm().move_single(body.servo_id, body.pwm, body.duration)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))


class MoveMultiRequest(BaseModel):
    pwms: dict[str, int]


@router.post("/move_multi")
def cal_move_multi(body: MoveMultiRequest, session: dict = Depends(require_role("admin"))):
    try:
        get_arm().move_to({int(k): int(v) for k, v in body.pwms.items()}, 1200)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(500, str(e))


class SaveCornerRequest(BaseModel):
    corner: str
    pwms: dict[str, int]


@router.post("/save_corner")
def cal_save_corner(body: SaveCornerRequest, session: dict = Depends(require_role("admin"))):
    cal = load_calibration()
    if "corners" not in cal:
        cal["corners"] = {}
    cal["corners"][body.corner] = body.pwms
    save_calibration(cal)
    return {"status": "ok", "corners": cal["corners"]}


class TestMoveRequest(BaseModel):
    corner: str


@router.post("/test_move")
def cal_test_move(body: TestMoveRequest, session: dict = Depends(require_role("admin"))):
    cal = load_calibration()
    corners = cal.get("corners", {})
    if body.corner not in corners:
        raise HTTPException(400, f"角 {body.corner} 未标定")
    pwms = {int(k): v for k, v in corners[body.corner].items()}
    get_arm().move_to(pwms, 1200)
    return {"status": "ok"}


@router.post("/reset")
def cal_reset(session: dict = Depends(require_role("admin"))):
    save_calibration({})
    return {"status": "ok"}


@router.post("/home")
def cal_home(session: dict = Depends(require_role("admin"))):
    arm = get_arm()
    mid = arm.neutral_value
    arm.move_to({i: mid for i in range(6)}, 1000)
    return {"status": "ok"}


@router.get("/config")
def cal_config(session: dict = Depends(get_session)):
    arm = get_arm()
    return {
        "arm_type": ARM_TYPE,
        "value_min": arm.value_min,
        "value_max": arm.value_max,
        "value_mid": arm.neutral_value,
    }
