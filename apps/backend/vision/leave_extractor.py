"""请假条 OCR 字段抽取模块"""
import re
from datetime import datetime


def extract_leave_fields(ocr_text: str, template_fields: list | None = None) -> dict:
    """从 OCR 文本中抽取请假条字段

    Args:
        ocr_text: OCR 识别后的完整文本
        template_fields: 可选的模板字段列表，用于自定义正则模式

    Returns:
        字段字典，包含 application_id, student_name, student_id, dept,
        leave_type, start_date, end_date, reason
    """
    text = ocr_text.strip()

    result = {
        'application_id': _extract_application_id(text),
        'student_name': _extract_student_name(text),
        'student_id': _extract_student_id(text),
        'dept': _extract_dept(text),
        'leave_type': _extract_leave_type(text),
        'start_date': _extract_date(text, 'start'),
        'end_date': _extract_date(text, 'end'),
        'reason': _extract_reason(text),
    }

    return result


def _extract_application_id(text: str) -> str | None:
    """抽取申请编号"""
    patterns = [
        r'申请编号[：:\s]*([A-Z]+-\d{8}-\d{4})',
        r'LEAVE[-_\s]?\d{8}[-_\s]?\d{4}',
        r'(LEAVE-\d{8}-\d{4})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).upper() if m.lastindex else m.group(0).upper()
    return None


def _extract_student_name(text: str) -> str | None:
    """抽取学生姓名"""
    patterns = [
        r'姓名[：:\s]*(\S{2,5})',
        r'学生[名姓名][：:\s]*(\S{2,5})',
        r'^(.{2,5})\s*(?:同学|先生|女士|学号)',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            name = m.group(1).strip()
            if len(name) >= 2:
                return name
    return None


def _extract_student_id(text: str) -> str | None:
    """抽取学号"""
    patterns = [
        r'学号[：:\s]*(\d{6,12})',
        r'学生编号[：:\s]*(\d{6,12})',
        r'工号[：:\s]*(\d{6,12})',
        r'(?<!\d)\d{8}(?!\d)',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1) if m.lastindex else m.group(0)
    return None


def _extract_dept(text: str) -> str | None:
    """抽取院系"""
    patterns = [
        r'院系[：:\s]*(\S{2,20})',
        r'学院[：:\s]*(\S{2,20})',
        r'系[：:\s]*(\S{2,20})',
        r'班级[：:\s]*(\S{2,20})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1).strip()
    return None


def _extract_leave_type(text: str) -> str | None:
    """抽取请假类型"""
    patterns = [
        r'请假类型[：:\s]*(病假|事假|婚假|产假|丧假|公假|其他)',
        r'(病假|事假|婚假|产假|丧假|公假|其他)',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1) if m.lastindex else m.group(0)
    return None


def _extract_date(text: str, which: str) -> str | None:
    """抽取日期（开始或结束）"""
    label = '开始' if which == 'start' else '结束'
    patterns = [
        rf'{label}日期?[：:\s]*(\d{{4}}[-年/]\d{{1,2}}[-月/]\d{{1,2}})',
        rf'{label}[期日期][：:\s]*(\d{{4}}[-年/]\d{{1,2}}[-月/]\d{{1,2}})',
        rf'(\d{{4}}[-年/]\d{{1,2}}[-月/]\d{{1,2}})\s*{label}',
        rf'{label}\s*[:：]\s*(\d{{4}}[-年/]\d{{1,2}}[-月/]\d{{1,2}})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            raw = m.group(1) if m.lastindex else m.group(0)
            return _normalize_date(raw)
    return None


def _extract_reason(text: str) -> str | None:
    """抽取请假原因"""
    patterns = [
        r'请假原因[：:\s]*(.{2,50})',
        r'原因[：:\s]*(.{2,50})',
        r'事由[：:\s]*(.{2,50})',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            reason = m.group(1).strip()
            if reason:
                return reason[:100]
    return None


def _normalize_date(raw: str) -> str:
    """将各种日期格式统一为 YYYY-MM-DD"""
    m = re.search(r'(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})', raw)
    if m:
        year, month, day = m.group(1), m.group(2), m.group(3)
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return raw.strip()


def get_ocr_patterns_dict(template_code: str) -> dict:
    """返回指定模板的字段名→ocr_pattern 字典。"""
    from database.template import get_ocr_patterns
    raw = get_ocr_patterns(template_code)
    return {r['field_name']: r['ocr_pattern'] for r in raw if r.get('ocr_pattern')}


def extract_leave_fields_from_template(ocr_text: str, template_code: str = 'leave') -> dict:
    """使用模板字段配置进行抽取（优先使用模板的 ocr_pattern）"""
    fields = extract_leave_fields(ocr_text)
    patterns = get_ocr_patterns_dict(template_code)
    if patterns:
        for field_name, pattern in patterns.items():
            if pattern:
                m = re.search(pattern, ocr_text)
                if m:
                    val = m.group(1) if m.lastindex else m.group(0)
                    if field_name in ('start_date', 'end_date'):
                        val = _normalize_date(val)
                    fields[field_name] = val
    return fields