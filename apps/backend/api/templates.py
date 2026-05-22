import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from api.deps import get_session, require_role
from database import template as tpl_db
from config import EXAMPLE_IMAGE_DIR

router = APIRouter(prefix="/templates", tags=["templates"])


class FieldInput(BaseModel):
    field_name: str
    field_label: str = ""
    field_category: str = "required"
    ocr_pattern: str = ""
    validation_rule: str = ""


class TemplateCreate(BaseModel):
    name: str
    code: str
    description: str = ""
    classification_keywords: list[str] = []
    classification_regex: str = ""
    requires_stamp: int = 1
    stamp_position: str = ""
    stamp_keywords: str = ""
    fields: list[FieldInput] = []


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    classification_keywords: list[str] | None = None
    classification_regex: str | None = None
    requires_stamp: int | None = None
    stamp_position: str | None = None
    stamp_keywords: str | None = None
    fields: list[FieldInput] | None = None


@router.get("")
def list_templates(session: dict = Depends(get_session)):
    templates = tpl_db.get_all_templates()
    return templates


@router.post("")
def create_template(
    body: TemplateCreate, session: dict = Depends(require_role("admin"))
):
    tid = tpl_db.create_template(
        name=body.name,
        code=body.code,
        description=body.description,
        classification_keywords=body.classification_keywords,
        classification_regex=body.classification_regex,
    )
    _save_stamp_config(
        tid, body.requires_stamp, body.stamp_position, body.stamp_keywords
    )
    for i, f in enumerate(body.fields):
        tpl_db.add_field(
            tid,
            f.field_name,
            f.field_label or f.field_name,
            f.field_category,
            f.ocr_pattern,
            f.validation_rule,
            i,
        )
    return {"id": tid, "status": "ok"}


@router.get("/{tid}")
def get_template(tid: int, session: dict = Depends(get_session)):
    template = tpl_db.get_template_by_id(tid)
    if not template:
        raise HTTPException(404, "模板不存在")
    return template


@router.put("/{tid}")
def update_template(
    tid: int, body: TemplateUpdate, session: dict = Depends(require_role("admin"))
):
    template = tpl_db.get_template_by_id(tid)
    if not template:
        raise HTTPException(404, "模板不存在")

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.classification_keywords is not None:
        updates["classification_keywords"] = body.classification_keywords
    if body.classification_regex is not None:
        updates["classification_regex"] = body.classification_regex

    if updates:
        tpl_db.update_template(tid, **updates)

    if (
        body.requires_stamp is not None
        or body.stamp_position is not None
        or body.stamp_keywords is not None
    ):
        _save_stamp_config(
            tid,
            (
                body.requires_stamp
                if body.requires_stamp is not None
                else template.get("requires_stamp", 1)
            ),
            (
                body.stamp_position
                if body.stamp_position is not None
                else template.get("stamp_position", "")
            ),
            (
                body.stamp_keywords
                if body.stamp_keywords is not None
                else template.get("stamp_keywords", "")
            ),
        )

    if body.fields is not None:
        tpl_db.replace_fields(tid, [f.model_dump() for f in body.fields])

    return {"status": "ok"}


@router.delete("/{tid}")
def delete_template(tid: int, session: dict = Depends(require_role("admin"))):
    ok = tpl_db.delete_template(tid)
    if ok:
        return {"status": "ok"}
    raise HTTPException(400, "系统预设模板不可删除")


@router.get("/{tid}/export")
def export_template(tid: int, session: dict = Depends(require_role("admin"))):
    template = tpl_db.get_template_by_id(tid)
    if not template:
        raise HTTPException(404, "模板不存在")
    data = _template_to_export_dict(template)
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={data['code']}.json"},
    )


@router.get("/export/all")
def export_all(session: dict = Depends(require_role("admin"))):
    templates = tpl_db.get_all_templates(with_fields=True)
    data = [_template_to_export_dict(t) for t in templates]
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=all_templates.json"},
    )


@router.post("/{tid}/generate_example")
def generate_example(tid: int, session: dict = Depends(require_role("admin"))):
    template = tpl_db.get_template_by_id(tid)
    if not template:
        raise HTTPException(404, "模板不存在")
    try:
        from vision.example_generator import generate_example_for_template

        os.makedirs(EXAMPLE_IMAGE_DIR, exist_ok=True)
        filename = f"{template['code']}_example.jpg"
        filepath = os.path.join(EXAMPLE_IMAGE_DIR, filename)
        img_bytes = generate_example_for_template(template)
        with open(filepath, "wb") as f:
            f.write(img_bytes)
        tpl_db.set_example_image(tid, filepath)
    except Exception as e:
        logging.exception("生成示例图片失败")
        raise HTTPException(500, str(e))
    return {"status": "ok"}


def _save_stamp_config(template_id, requires, stamp_pos, stamp_kw):
    from database.connection import get_db
    from sqlalchemy import text

    with get_db() as conn:
        conn.execute(
            text(
                "UPDATE doc_templates SET requires_stamp=:rs, stamp_position=:sp, "
                "stamp_keywords=:sk WHERE id=:id"
            ),
            {"rs": int(requires), "sp": stamp_pos, "sk": stamp_kw, "id": template_id},
        )


def _template_to_export_dict(template: dict) -> dict:
    kw = template.get("classification_keywords", "[]")
    if isinstance(kw, str):
        try:
            kw = json.loads(kw)
        except (json.JSONDecodeError, TypeError):
            kw = []
    return {
        "name": template.get("name", ""),
        "code": template.get("code", ""),
        "description": template.get("description", ""),
        "is_system": template.get("is_system", 0),
        "sort_order": template.get("sort_order", 0),
        "classification_keywords": kw,
        "classification_regex": template.get("classification_regex", ""),
        "requires_stamp": template.get("requires_stamp", 1),
        "stamp_position": template.get("stamp_position", ""),
        "stamp_keywords": template.get("stamp_keywords", ""),
        "fields": [
            {
                "field_name": f.get("field_name", ""),
                "field_label": f.get("field_label", ""),
                "field_category": f.get("field_category", "required"),
                "ocr_pattern": f.get("ocr_pattern", ""),
                "validation_rule": f.get("validation_rule", ""),
            }
            for f in template.get("fields", [])
        ],
    }
