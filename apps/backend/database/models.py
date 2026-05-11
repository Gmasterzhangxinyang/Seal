from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Personnel(Base):
    __tablename__ = 'personnel'

    id_number: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    dept: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str | None] = mapped_column(String(50))


class AuditLog(Base):
    __tablename__ = 'audit_log'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String(30), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(50), nullable=False)
    doc_type: Mapped[str | None] = mapped_column(String(50))
    qr_content: Mapped[str | None] = mapped_column(String(500))
    doc_fields: Mapped[str | None] = mapped_column(Text)
    ocr_text: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    errors: Mapped[str | None] = mapped_column(Text)
    before_img: Mapped[str | None] = mapped_column(String(500))
    after_img: Mapped[str | None] = mapped_column(String(500))
    dms_doc_id: Mapped[str | None] = mapped_column(String(100))


class ReviewQueue(Base):
    __tablename__ = 'review_queue'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[str] = mapped_column(String(30), nullable=False)
    operator_id: Mapped[str] = mapped_column(String(50), nullable=False)
    doc_type: Mapped[str | None] = mapped_column(String(50))
    doc_fields: Mapped[str | None] = mapped_column(Text)
    ocr_text: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[str | None] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default='pending')
    reviewer_id: Mapped[str | None] = mapped_column(String(50))
    resolved_at: Mapped[str | None] = mapped_column(String(30))
    decision: Mapped[str | None] = mapped_column(String(20))
    stamped: Mapped[int | None] = mapped_column(Integer, server_default='0')


class User(Base):
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(String(50), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default='operator')
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)


class DocTemplate(Base):
    __tablename__ = 'doc_templates'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[int] = mapped_column(Integer, nullable=False, server_default='0')
    classification_keywords: Mapped[str | None] = mapped_column(Text)
    classification_regex: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, server_default='0')
    requires_stamp: Mapped[int] = mapped_column(Integer, server_default='1')
    stamp_position: Mapped[str] = mapped_column(String(100), server_default='')
    stamp_keywords: Mapped[str | None] = mapped_column(Text)


class TemplateField(Base):
    __tablename__ = 'template_fields'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('doc_templates.id', ondelete='CASCADE'), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_label: Mapped[str] = mapped_column(String(100), nullable=False)
    field_category: Mapped[str] = mapped_column(String(20), nullable=False, server_default='required')
    ocr_pattern: Mapped[str | None] = mapped_column(Text)
    validation_rule: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, server_default='0')


class TemplateExample(Base):
    __tablename__ = 'template_examples'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('doc_templates.id', ondelete='CASCADE'), nullable=False, unique=True
    )
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_at: Mapped[str] = mapped_column(String(30), nullable=False)


# ─── 请假申请相关模型 ──────────────────────────────────────────────────────────

class LeaveApplication(Base):
    __tablename__ = 'leave_applications'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    student_id: Mapped[str] = mapped_column(String(20), nullable=False)
    student_name: Mapped[str] = mapped_column(String(50), nullable=False)
    dept: Mapped[str | None] = mapped_column(String(100))
    leave_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[str] = mapped_column(String(30), nullable=False)
    end_date: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default='SUBMITTED')
    qr_content: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(String(50))
    approved_at: Mapped[str | None] = mapped_column(String(30))
    stamped_at: Mapped[str | None] = mapped_column(String(30))
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False)


class StampTask(Base):
    __tablename__ = 'stamp_tasks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    application_id: Mapped[str | None] = mapped_column(String(64))
    operator_id: Mapped[str | None] = mapped_column(String(50))
    doc_type: Mapped[str] = mapped_column(String(50), server_default='leave')
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    decision: Mapped[str | None] = mapped_column(String(30))
    risk_score: Mapped[int] = mapped_column(Integer, server_default='0')
    before_img: Mapped[str | None] = mapped_column(String(500))
    after_img: Mapped[str | None] = mapped_column(String(500))
    qr_content: Mapped[str | None] = mapped_column(Text)
    extracted_fields: Mapped[str | None] = mapped_column(Text)
    verification_result: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False)


class VerificationResult(Base):
    __tablename__ = 'verification_results'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    check_name: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    score: Mapped[int] = mapped_column(Integer, server_default='0')
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(30), nullable=False)


def init_db():
    """创建所有不存在的表。"""
    from database.connection import engine
    Base.metadata.create_all(engine)
