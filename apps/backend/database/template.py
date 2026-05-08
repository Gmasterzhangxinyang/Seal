import json
from datetime import datetime
from sqlalchemy import text
from database.connection import get_db


# ─── 模板 CRUD ─────────────────────────────────────────────────────────────────

def create_template(name, code, description='', classification_keywords=None,
                    classification_regex='', is_system=0, sort_order=0) -> int:
    with get_db() as conn:
        r = conn.execute(text(
            '''INSERT INTO doc_templates
               (name, code, description, is_system, classification_keywords,
                classification_regex, created_at, updated_at, sort_order)
               VALUES (:name, :code, :desc, :is_sys, :kw, :re, :cat, :uat, :so)'''
        ), {
            'name': name, 'code': code, 'desc': description, 'is_sys': is_system,
            'kw': json.dumps(classification_keywords or [], ensure_ascii=False),
            're': classification_regex,
            'cat': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'uat': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'so': sort_order,
        })
        tid = r.lastrowid
    assert tid is not None
    return tid


def get_template_by_id(template_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(text(
            'SELECT * FROM doc_templates WHERE id=:id'
        ), {'id': template_id}).mappings().one_or_none()
    if not row:
        return None
    tpl = dict(row)
    tpl['fields'] = get_fields_for_template(template_id)
    tpl['example_image'] = get_example_image(template_id)
    return tpl


def get_template_by_code(code: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(text(
            'SELECT * FROM doc_templates WHERE code=:code'
        ), {'code': code}).mappings().one_or_none()
    if not row:
        return None
    tpl = dict(row)
    tpl['fields'] = get_fields_for_template(tpl['id'])
    tpl['example_image'] = get_example_image(tpl['id'])
    return tpl


def get_all_templates(with_fields=False) -> list:
    with get_db() as conn:
        rows = conn.execute(text(
            'SELECT * FROM doc_templates ORDER BY sort_order, id'
        )).mappings().all()
    result = []
    for row in rows:
        tpl = dict(row)
        if with_fields:
            tpl['fields'] = get_fields_for_template(tpl['id'])
            tpl['example_image'] = get_example_image(tpl['id'])
        else:
            tpl['fields'] = get_fields_for_template(tpl['id'])
            tpl['field_stats'] = _compute_field_stats(tpl['fields'])
            tpl['example_image'] = get_example_image(tpl['id'])
        result.append(tpl)
    return result


def _compute_field_stats(fields):
    stats = {'required': 0, 'optional': 0, 'forbidden': 0}
    for f in fields:
        cat = f.get('field_category', 'required')
        if cat in stats:
            stats[cat] += 1
    return stats


def update_template(template_id: int, **kwargs) -> bool:
    allowed = {'name', 'code', 'description', 'classification_keywords',
               'classification_regex', 'sort_order', 'updated_at'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    if 'classification_keywords' in updates and isinstance(updates['classification_keywords'], list):
        updates['classification_keywords'] = json.dumps(updates['classification_keywords'], ensure_ascii=False)
    updates['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sets = ', '.join(f'{k}=:{k}' for k in updates)
    updates['id'] = template_id
    with get_db() as conn:
        conn.execute(text(f'UPDATE doc_templates SET {sets} WHERE id=:id'), updates)
    return True


def delete_template(template_id: int) -> bool:
    with get_db() as conn:
        row = conn.execute(text(
            'SELECT is_system FROM doc_templates WHERE id=:id'
        ), {'id': template_id}).fetchone()
        if not row or row[0]:
            return False
        conn.execute(text('DELETE FROM template_fields WHERE template_id=:id'), {'id': template_id})
        conn.execute(text('DELETE FROM template_examples WHERE template_id=:id'), {'id': template_id})
        conn.execute(text('DELETE FROM doc_templates WHERE id=:id'), {'id': template_id})
    return True


# ─── 字段管理 ─────────────────────────────────────────────────────────────────

def add_field(template_id, field_name, field_label, field_category='required',
              ocr_pattern='', validation_rule='', sort_order=0) -> int:
    with get_db() as conn:
        r = conn.execute(text(
            '''INSERT INTO template_fields
               (template_id, field_name, field_label, field_category,
                ocr_pattern, validation_rule, sort_order)
               VALUES (:tid, :fn, :fl, :fc, :op, :vr, :so)'''
        ), {
            'tid': template_id, 'fn': field_name, 'fl': field_label,
            'fc': field_category, 'op': ocr_pattern, 'vr': validation_rule,
            'so': sort_order,
        })
        fid = r.lastrowid
    assert fid is not None
    return fid


def update_field(field_id: int, **kwargs) -> bool:
    allowed = {'field_name', 'field_label', 'field_category', 'ocr_pattern',
               'validation_rule', 'sort_order'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    sets = ', '.join(f'{k}=:{k}' for k in updates)
    updates['id'] = field_id
    with get_db() as conn:
        conn.execute(text(f'UPDATE template_fields SET {sets} WHERE id=:id'), updates)
    return True


def delete_field(field_id: int):
    with get_db() as conn:
        conn.execute(text('DELETE FROM template_fields WHERE id=:id'), {'id': field_id})


def get_fields_for_template(template_id: int) -> list:
    with get_db() as conn:
        rows = conn.execute(text(
            'SELECT * FROM template_fields WHERE template_id=:id ORDER BY sort_order, id'
        ), {'id': template_id}).mappings().all()
    return [dict(r) for r in rows]


def replace_fields(template_id: int, fields_data: list):
    """替换模板的所有字段。"""
    with get_db() as conn:
        conn.execute(text(
            'DELETE FROM template_fields WHERE template_id=:id'
        ), {'id': template_id})
        for i, fd in enumerate(fields_data):
            conn.execute(text(
                '''INSERT INTO template_fields
                   (template_id, field_name, field_label, field_category,
                    ocr_pattern, validation_rule, sort_order)
                   VALUES (:tid, :fn, :fl, :fc, :op, :vr, :so)'''
            ), {
                'tid': template_id,
                'fn': fd.get('field_name', ''),
                'fl': fd.get('field_label', fd.get('field_name', '')),
                'fc': fd.get('field_category', 'required'),
                'op': fd.get('ocr_pattern', ''),
                'vr': fd.get('validation_rule', ''),
                'so': i,
            })


# ─── 分类辅助 ─────────────────────────────────────────────────────────────────

def get_all_classification_rules() -> list:
    with get_db() as conn:
        rows = conn.execute(text(
            '''SELECT id, code, name, classification_keywords, classification_regex
               FROM doc_templates WHERE is_system=1 OR code!='general'
               ORDER BY sort_order'''
        )).fetchall()
    result = []
    for row in rows:
        result.append({
            'id': row[0], 'code': row[1], 'name': row[2],
            'keywords': json.loads(row[3]) if row[3] else [],
            'regex': row[4] or '',
        })
    return result


# ─── 示例图片 ─────────────────────────────────────────────────────────────────

def set_example_image(template_id: int, image_path: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        conn.execute(text(
            '''INSERT INTO template_examples (template_id, image_path, generated_at)
               VALUES (:tid, :img, :ts)
               ON DUPLICATE KEY UPDATE image_path=VALUES(image_path), generated_at=VALUES(generated_at)'''
        ), {'tid': template_id, 'img': image_path, 'ts': ts})


def get_example_image(template_id: int) -> str | None:
    with get_db() as conn:
        row = conn.execute(text(
            'SELECT image_path FROM template_examples WHERE template_id=:id'
        ), {'id': template_id}).fetchone()
    return row[0] if row else None


def get_type_name_map() -> dict:
    with get_db() as conn:
        rows = conn.execute(text('SELECT code, name FROM doc_templates')).fetchall()
    return {r[0]: r[1] for r in rows}


def get_ocr_patterns(template_code: str) -> list[dict]:
    """返回指定模板的所有字段及其 ocr_pattern。"""
    with get_db() as conn:
        row = conn.execute(text(
            'SELECT id FROM doc_templates WHERE code=:code'
        ), {'code': template_code}).fetchone()
        if not row:
            return []
        rows = conn.execute(text(
            'SELECT field_name, ocr_pattern, field_category '
            'FROM template_fields WHERE template_id=:id ORDER BY sort_order, id'
        ), {'id': row[0]}).fetchall()
    return [{'field_name': r[0], 'ocr_pattern': r[1], 'field_category': r[2]} for r in rows]
