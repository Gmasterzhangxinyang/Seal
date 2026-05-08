from datetime import datetime

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from database.connection import get_db


def seed_demo_data():
    """写入演示人员 + 账号（已存在则跳过）。"""
    personnel = [
        {'id': '20210001', 'name': '张三', 'dept': '计算机学院', 'role': 'student'},
        {'id': '20210002', 'name': '李四', 'dept': '计算机学院', 'role': 'student'},
        {'id': '20210003', 'name': '王五', 'dept': '电子工程学院', 'role': 'student'},
        {'id': 'T001',     'name': '陈邦翔', 'dept': '教务处', 'role': 'staff'},
    ]
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    users = [
        {'u': 'admin',     'pw': generate_password_hash('admin123'),     'r': 'admin',
         'e': 'admin@example.com', 't': now},
        {'u': 'operator1', 'pw': generate_password_hash('op123'),        'r': 'operator',
         'e': 'operator1@example.com', 't': now},
        {'u': 'reviewer1', 'pw': generate_password_hash('reviewer123'),  'r': 'reviewer',
         'e': 'reviewer1@example.com', 't': now},
    ]

    with get_db() as conn:
        for p in personnel:
            conn.execute(text(
                'INSERT IGNORE INTO personnel (id_number, name, dept, role) '
                'VALUES (:id, :name, :dept, :role)'
            ), p)
        for u in users:
            conn.execute(text(
                'INSERT IGNORE INTO users (username, password_hash, email, role, created_at) '
                'VALUES (:u, :pw, :e, :r, :t)'
            ), u)
            conn.execute(text(
                'UPDATE users SET email=:e, created_at=:t '
                'WHERE username=:u AND (email IS NULL OR email = \'\' OR created_at IS NULL OR created_at = \'\')'
            ), u)


def seed_default_templates():
    """写入预设文档模板和字段定义（单连接，无嵌套事务）。"""
    import json
    from datetime import datetime
    from sqlalchemy import text
    from database.connection import get_db

    templates = [
        {
            'name': '请假条', 'code': 'leave',
            'description': '学生请假申请文件，包含请假原因、天数等信息',
            'is_system': 1, 'sort_order': 1,
            'keywords': ['请假', '事假', '病假', '公假', '请假条', '请假申请', '请假类型', '请假天数'],
            'regex': '请假',
            'requires_stamp': 1, 'stamp_position': '0.82,0.85',
            'stamp_keywords': '盖章处,审批人,辅导员意见',
            'fields': [
                ('姓名', '姓名', 'required',
                 r'姓\s*名\s*[：:]\s*(\S{2,5})',
                 '{"regex": "\\S{2,5}", "min_length": 2, "max_length": 5}'),
                ('学号', '学号', 'required',
                 r'(?:学号|工号|学生编号)\s*[：:]\s*(\d{6,12})',
                 '{"regex": "^\\d{6,12}$"}'),
                ('日期', '日期', 'required',
                 r'(\d{4})\s*[-年/]\s*(\d{1,2})\s*[-月/]\s*(\d{1,2})\s*日?',
                 '{"date_format": "%Y-%m-%d"}'),
                ('原因', '请假原因', 'required',
                 r'(?:原因|事由|请假原因)\s*[：:]\s*(.{2,30})',
                 '{"min_length": 2, "max_length": 30}'),
                ('请假类型', '请假类型', 'optional',
                 r'(?:请假类型|假别)\s*[：:]\s*(\S{2,10})',
                 '{"allowed_values": ["事假", "病假", "公假", "丧假", "婚假"]}'),
                ('金额', '报销金额', 'forbidden', '', ''),
            ],
        },
        {
            'name': '报销申请表', 'code': 'expense',
            'description': '费用报销申请文件，包含金额、用途等信息',
            'is_system': 1, 'sort_order': 2,
            'keywords': ['报销', '费用', '金额', '合计', '总计', '用途', '报销单', '报销申请'],
            'regex': '报销',
            'requires_stamp': 1, 'stamp_position': '0.80,0.85',
            'stamp_keywords': '盖章处,审批人,财务审核',
            'fields': [
                ('姓名', '姓名', 'required',
                 r'姓\s*名\s*[：:]\s*(\S{2,5})',
                 '{"regex": "\\S{2,5}", "min_length": 2, "max_length": 5}'),
                ('学号', '学号', 'required',
                 r'(?:学号|工号|学生编号)\s*[：:]\s*(\d{6,12})',
                 '{"regex": "^\\d{6,12}$"}'),
                ('日期', '日期', 'required',
                 r'(\d{4})\s*[-年/]\s*(\d{1,2})\s*[-月/]\s*(\d{1,2})\s*日?',
                 '{"date_format": "%Y-%m-%d"}'),
                ('金额', '报销金额', 'required',
                 r'(?:金额|合计|总计)\s*[：:￥¥]?\s*(\d+(?:\.\d{1,2})?)\s*元?',
                 '{"regex": "^\\d+(\\.\\d{1,2})?$", "min_value": 0.01, "max_value": 100000}'),
                ('用途', '报销用途', 'optional',
                 r'(?:用途|事由|说明)\s*[：:]\s*(.{2,50})',
                 '{"min_length": 2}'),
                ('原因', '请假原因', 'forbidden', '', ''),
            ],
        },
        {
            'name': '证明申请', 'code': 'cert',
            'description': '各类证明文件申请，如在读证明、成绩证明等',
            'is_system': 1, 'sort_order': 3,
            'keywords': ['证明', '在读', '成绩', '学籍', '毕业', '证明申请'],
            'regex': '证明',
            'requires_stamp': 1, 'stamp_position': '0.75,0.80',
            'stamp_keywords': '盖章处,学院公章,教务处',
            'fields': [
                ('姓名', '姓名', 'required',
                 r'姓\s*名\s*[：:]\s*(\S{2,5})',
                 '{"regex": "\\S{2,5}", "min_length": 2, "max_length": 5}'),
                ('学号', '学号', 'required',
                 r'(?:学号|工号|学生编号)\s*[：:]\s*(\d{6,12})',
                 '{"regex": "^\\d{6,12}$"}'),
                ('日期', '日期', 'required',
                 r'(\d{4})\s*[-年/]\s*(\d{1,2})\s*[-月/]\s*(\d{1,2})\s*日?',
                 '{"date_format": "%Y-%m-%d"}'),
                ('证明类型', '证明类型', 'optional',
                 r'(?:证明类型|类型)\s*[：:]\s*(\S{2,20})',
                 '{"allowed_values": ["在读证明", "成绩证明", "毕业证明", "学位证明", "学籍证明"]}'),
                ('金额', '报销金额', 'forbidden', '', ''),
            ],
        },
        {
            'name': '通用文件', 'code': 'general',
            'description': '无法归类的通用文件，仅检查基本字段',
            'is_system': 1, 'sort_order': 99,
            'keywords': [], 'regex': '',
            'requires_stamp': 1, 'stamp_position': '0.82,0.85',
            'stamp_keywords': '盖章处,签名,签字',
            'fields': [
                ('姓名', '姓名', 'required',
                 r'姓\s*名\s*[：:]\s*(\S{2,5})',
                 '{"regex": "\\S{2,5}"}'),
                ('日期', '日期', 'required',
                 r'(\d{4})\s*[-年/]\s*(\d{1,2})\s*[-月/]\s*(\d{1,2})\s*日?',
                 '{"date_format": "%Y-%m-%d"}'),
            ],
        },
    ]

    with get_db() as conn:
        for tpl in templates:
            row = conn.execute(text(
                'SELECT id FROM doc_templates WHERE code=:code'
            ), {'code': tpl['code']}).fetchone()
            if row:
                conn.execute(text(
                    'UPDATE doc_templates SET requires_stamp=:rs, stamp_position=:sp, '
                    'stamp_keywords=:sk WHERE id=:id'
                ), {
                    'rs': tpl['requires_stamp'], 'sp': tpl['stamp_position'],
                    'sk': tpl['stamp_keywords'], 'id': row[0],
                })
                continue
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            r = conn.execute(text(
                '''INSERT INTO doc_templates
                   (name, code, description, is_system, classification_keywords,
                    classification_regex, created_at, updated_at, sort_order,
                    requires_stamp, stamp_position, stamp_keywords)
                   VALUES (:name, :code, :desc, :is_sys, :kw, :re, :cat, :uat, :so,
                           :rs, :sp, :sk)'''
            ), {
                'name': tpl['name'], 'code': tpl['code'], 'desc': tpl['description'],
                'is_sys': tpl['is_system'],
                'kw': json.dumps(tpl['keywords'], ensure_ascii=False),
                're': tpl['regex'], 'cat': now, 'uat': now, 'so': tpl['sort_order'],
                'rs': tpl['requires_stamp'], 'sp': tpl['stamp_position'],
                'sk': tpl['stamp_keywords'],
            })
            tid = r.lastrowid
            for i, fd in enumerate(tpl['fields']):
                conn.execute(text(
                    '''INSERT INTO template_fields
                       (template_id, field_name, field_label, field_category,
                        ocr_pattern, validation_rule, sort_order)
                       VALUES (:tid, :fn, :fl, :fc, :op, :vr, :so)'''
                ), {
                    'tid': tid, 'fn': fd[0], 'fl': fd[1], 'fc': fd[2],
                    'op': fd[3], 'vr': fd[4], 'so': i,
                })
