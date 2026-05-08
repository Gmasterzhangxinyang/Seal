import logging

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_session

router = APIRouter(tags=["stamp"])

_processor = None


def get_processor():
    global _processor
    if _processor is None:
        from main import DocumentProcessor
        _processor = DocumentProcessor()
    return _processor


@router.post("/stamp")
def stamp(session: dict = Depends(get_session)):
    try:
        logging.info("[stamp] 开始处理，用户: %s", session["username"])
        result = get_processor().process(session["username"])
        return result
    except Exception as e:
        logging.exception("[stamp] 处理文件时出错")
        raise HTTPException(500, str(e))


@router.post("/review/{review_id}/stamp")
def review_stamp(review_id: int, session: dict = Depends(get_session)):
    try:
        result = get_processor().process_review_stamping(review_id, session["username"])
        return result
    except Exception as e:
        logging.exception("复审盖章失败")
        raise HTTPException(500, str(e))
