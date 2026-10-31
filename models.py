from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Index, JSON, UniqueConstraint
from sqlalchemy.orm import synonym


db = SQLAlchemy()

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.role_id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.permission_id"), primary_key=True),
)

user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("users.user_id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.role_id"), primary_key=True),
    db.Column("assigned_at", db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)),
    db.Column("assigned_by", db.Integer, db.ForeignKey("users.user_id")),
)


def utcnow():
    return datetime.now(timezone.utc)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column("role_id", db.Integer, primary_key=True)
    name = db.Column("role_name", db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    permissions = db.relationship("Permission", secondary=role_permissions, lazy="selectin")
    users = db.relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
        foreign_keys=[user_roles.c.user_id, user_roles.c.role_id],
    )


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column("permission_id", db.Integer, primary_key=True)
    name = db.Column("permission_name", db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    module = db.Column(db.String(50))


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column("department_id", db.Integer, primary_key=True)
    name = db.Column("department_name", db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    email = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    categories = db.relationship("Category", back_populates="department_record")
    users = db.relationship("User", back_populates="department_record")


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "user_type IN ('STUDENT', 'FACULTY', 'WORKING_STAFF')",
            name="ck_users_user_type",
        ),
    )

    id = db.Column("user_id", db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column("name", db.String(255), nullable=False)
    password_hash = db.Column(db.String(256))
    google_subject = db.Column("google_id", db.String(255), unique=True)
    user_type = db.Column(db.String(50), nullable=False, default="STUDENT")
    department_id = db.Column(db.Integer, db.ForeignKey("departments.department_id", ondelete="SET NULL"))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    last_login = db.Column(db.DateTime(timezone=True))
    profile_picture_url = db.Column(db.Text)
    department_record = db.relationship("Department", back_populates="users", foreign_keys=[department_id])
    roles = db.relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
        foreign_keys=[user_roles.c.user_id, user_roles.c.role_id],
    )

    @property
    def role(self):
        return self.roles[0] if self.roles else None

    @role.setter
    def role(self, value):
        self.roles = [value] if value is not None else []

    @property
    def department(self):
        return self.department_record.name if self.department_record else None

    @department.setter
    def department(self, value):
        self.department_record = Department.query.filter_by(name=value).first() if value else None

    def to_dict(self):
        role = self.role
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "user_type": self.user_type,
            "role": role.name if role else None,
            "department": self.department,
            "is_active": self.is_active,
        }


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("category_name", "department_id", name="uq_category_department_name"),)

    id = db.Column("category_id", db.Integer, primary_key=True)
    name = db.Column("category_name", db.String(100), nullable=False)
    description = db.Column(db.Text)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.department_id", ondelete="CASCADE"), nullable=False)
    sla_hours = db.Column(db.Integer, default=24)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    department_record = db.relationship("Department", back_populates="categories")

    @property
    def department(self):
        return self.department_record.name if self.department_record else None

    @department.setter
    def department(self, value):
        self.department_record = Department.query.filter_by(name=value).first() if value else None


class Complaint(db.Model):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')",
            name="ck_complaints_priority",
        ),
        CheckConstraint(
            "status IN ('SUBMITTED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'REJECTED')",
            name="ck_complaints_status",
        ),
    )

    id = db.Column("complaint_id", db.Integer, primary_key=True)
    reporter_id = db.Column("user_id", db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.category_id", ondelete="SET NULL"))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.department_id", ondelete="SET NULL"))
    priority = db.Column(db.String(20), nullable=False, default="MEDIUM")
    status = db.Column(db.String(50), nullable=False, default="SUBMITTED", index=True)
    urgency_score = db.Column(db.Integer, default=0)
    location = db.Column(db.String(255))
    attachment_urls = db.Column(db.ARRAY(db.Text).with_variant(JSON, "sqlite"))
    submission_mode = db.Column(db.String(20), nullable=False, default="WEB")
    is_duplicate = db.Column(db.Boolean, nullable=False, default=False)
    duplicate_of = db.Column(db.Integer, db.ForeignKey("complaints.complaint_id", ondelete="SET NULL"))
    confidence_score = db.Column(db.Float, default=0.0)
    ai_suggested_department_id = db.Column(db.Integer, db.ForeignKey("departments.department_id", ondelete="SET NULL"))
    ai_suggested_priority = db.Column(db.String(20))
    rag_relevant_docs = db.Column(db.ARRAY(db.Text).with_variant(JSON, "sqlite"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    resolved_at = db.Column(db.DateTime(timezone=True))

    reporter = db.relationship("User", foreign_keys=[reporter_id])
    department_record = db.relationship("Department", foreign_keys=[department_id])
    category_record = db.relationship("Category")
    history_entries = db.relationship(
        "ComplaintHistory",
        back_populates="complaint",
        order_by="ComplaintHistory.created_at",
    )

    @property
    def reference(self):
        return f"CMP-{self.id:06d}" if self.id is not None else "CMP-PENDING"

    @property
    def department(self):
        return self.department_record.name if self.department_record else None

    @department.setter
    def department(self, value):
        self.department_record = Department.query.filter_by(name=value).first() if value else None

    @property
    def assigned_to_id(self):
        return None

    @property
    def assigned_to(self):
        return None

    @property
    def suggested_resolution(self):
        for event in reversed(self.history_entries):
            if event.action == "AI_SUGGESTION":
                return event.note or ""
        return ""

    @property
    def resolution(self):
        for event in reversed(self.history_entries):
            if event.action == "RESOLVED":
                return event.note or ""
        return ""

    @property
    def ai_metadata(self):
        return {
            "department": self.department,
            "priority": self.priority,
            "confidence_score": self.confidence_score,
            "suggested_department_id": self.ai_suggested_department_id,
            "suggested_priority": self.ai_suggested_priority,
            "relevant_documents": self.rag_relevant_docs or [],
        }

    def to_dict(self, include_description=True):
        result = {
            "id": self.id,
            "reference": self.reference,
            "reporter": self.reporter.full_name if self.reporter else None,
            "reporter_id": self.reporter_id,
            "title": self.title,
            "location": self.location,
            "department": self.department,
            "category": self.category_record.name if self.category_record else None,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": None,
            "assigned_to_id": None,
            "suggested_resolution": self.suggested_resolution,
            "resolution": self.resolution,
            "ai": self.ai_metadata,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_description:
            result["description"] = self.description
        return result


class ComplaintHistory(db.Model):
    __tablename__ = "complaint_history"

    id = db.Column("history_id", db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = db.Column("changed_by", db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    action = db.Column("change_type", db.String(50), nullable=False)
    before_state = db.Column("old_values", db.JSON)
    after_state = db.Column("new_values", db.JSON)
    changed_field = db.Column(db.String(100))
    note = db.Column("change_description", db.Text)
    created_at = db.Column("changed_at", db.DateTime(timezone=True), nullable=False, default=utcnow)
    ip_address = db.Column(db.String(45))
    actor = db.relationship("User")
    complaint = db.relationship("Complaint", back_populates="history_entries")

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.full_name if self.actor else "System",
            "action": self.action,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "note": self.note or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column("log_id", db.Integer, primary_key=True)
    actor_id = db.Column("user_id", db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50))
    resource_id = db.Column(db.Integer)
    old_values = db.Column(db.JSON)
    details = db.Column("new_values", db.JSON)
    status = db.Column(db.String(20))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.full_name if self.actor else "System",
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Feedback(db.Model):
    __tablename__ = "feedback"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating"),)

    id = db.Column("feedback_id", db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    is_helpful = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class BackupRecord(db.Model):
    __tablename__ = "backup_records"

    id = db.Column("backup_id", db.Integer, primary_key=True)
    actor_id = db.Column("created_by", db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    filename = db.Column("backup_name", db.String(255), unique=True, nullable=False)
    operation = db.Column("backup_type", db.String(50))
    backup_location = db.Column(db.Text)
    size_mb = db.Column(db.Integer)
    status = db.Column(db.String(20))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True))
    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.full_name if self.actor else None,
            "filename": self.filename,
            "operation": self.operation,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RollbackRecord(db.Model):
    __tablename__ = "rollback_records"

    id = db.Column("rollback_id", db.Integer, primary_key=True)
    backup_id = db.Column(db.Integer, db.ForeignKey("backup_records.backup_id", ondelete="SET NULL"))
    actor_id = db.Column("initiated_by", db.Integer, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    status = db.Column(db.String(20))
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = db.Column(db.DateTime(timezone=True))


class ComplaintEmbedding(db.Model):
    __tablename__ = "complaint_embeddings"
    __table_args__ = (
        Index(
            "idx_complaint_embeddings_vector",
            "embedding_vector",
            postgresql_using="hnsw",
            postgresql_ops={"embedding_vector": "vector_cosine_ops"},
        ),
    )

    id = db.Column("embedding_id", db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False, unique=True)
    embedding_vector = db.Column(JSON().with_variant(Vector(384), "postgresql"))
    embedding = synonym("embedding_vector")
    model_name = db.Column("embedding_model", db.String(100), nullable=False, default="sentence-transformers/all-MiniLM-L6-v2")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    complaint = db.relationship("Complaint", backref=db.backref("embedding_record", uselist=False))


class KnowledgeDocumentChunk(db.Model):
    __tablename__ = "knowledge_document_chunks"
    __table_args__ = (
        Index(
            "idx_knowledge_chunks_embedding",
            "chunk_embedding",
            postgresql_using="hnsw",
            postgresql_ops={"chunk_embedding": "vector_cosine_ops"},
        ),
        UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_document_chunk_index"),
    )

    id = db.Column("chunk_id", db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.department_id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column("chunk_text", db.Text, nullable=False)
    chunk_index = db.Column(db.Integer)
    chunk_embedding = db.Column(JSON().with_variant(Vector(384), "postgresql"))
    embedding = synonym("chunk_embedding")
    model_name = db.Column("embedding_model", db.String(100), nullable=False, default="sentence-transformers/all-MiniLM-L6-v2")
    metadata_json = db.Column("metadata", db.JSON)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    department_record = db.relationship("Department")

    @property
    def department(self):
        return self.department_record.name if self.department_record else None

    @property
    def source(self):
        return (self.metadata_json or {}).get("source", f"document:{self.document_id}")
