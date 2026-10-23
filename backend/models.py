from datetime import datetime, timezone
from uuid import uuid4

from flask_sqlalchemy import SQLAlchemy
from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Index, JSON, UniqueConstraint


db = SQLAlchemy()
role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.String(36), db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permission_id", db.String(36), db.ForeignKey("permissions.id"), primary_key=True),
)


def utcnow():
    return datetime.now(timezone.utc)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    name = db.Column(db.String(30), unique=True, nullable=False)
    permissions = db.relationship("Permission", secondary=role_permissions, lazy="selectin")


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    name = db.Column(db.String(60), unique=True, nullable=False)


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "user_type IN ('STUDENT', 'FACULTY', 'WORKING_STAFF')",
            name="ck_users_user_type",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256))
    google_subject = db.Column(db.String(255), unique=True)
    user_type = db.Column(db.String(20), nullable=False, default="STUDENT")
    role_id = db.Column(db.String(36), db.ForeignKey("roles.id"), nullable=False)
    department = db.Column(db.String(30), db.ForeignKey("departments.name"))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    role = db.relationship("Role")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "user_type": self.user_type,
            "role": self.role.name,
            "department": self.department,
            "is_active": self.is_active,
        }


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    name = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(240), nullable=False, default="")


class Category(db.Model):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("department", "name", name="uq_category_department_name"),)

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    department = db.Column(db.String(30), db.ForeignKey("departments.name"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)


class Complaint(db.Model):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')",
            name="ck_complaints_priority",
        ),
        CheckConstraint(
            "status IN ('SUBMITTED', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', 'REOPENED')",
            name="ck_complaints_status",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    reference = db.Column(db.String(16), unique=True, nullable=False, index=True)
    reporter_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(160), nullable=False, default="")
    department = db.Column(db.String(30), db.ForeignKey("departments.name"), nullable=False, index=True)
    category_id = db.Column(db.String(36), db.ForeignKey("categories.id"), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="MEDIUM")
    status = db.Column(db.String(24), nullable=False, default="SUBMITTED", index=True)
    assigned_to_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    suggested_resolution = db.Column(db.Text, nullable=False, default="")
    resolution = db.Column(db.Text, nullable=False, default="")
    ai_metadata = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    reporter = db.relationship("User", foreign_keys=[reporter_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    category_record = db.relationship("Category")

    def to_dict(self, include_description=True):
        result = {
            "id": self.id,
            "reference": self.reference,
            "reporter": self.reporter.full_name,
            "reporter_id": self.reporter_id,
            "title": self.title,
            "location": self.location,
            "department": self.department,
            "category": self.category_record.name,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": self.assigned_to.full_name if self.assigned_to else None,
            "assigned_to_id": self.assigned_to_id,
            "suggested_resolution": self.suggested_resolution,
            "resolution": self.resolution,
            "ai": self.ai_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_description:
            result["description"] = self.description
        return result


class ComplaintHistory(db.Model):
    __tablename__ = "complaint_history"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False, index=True)
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(40), nullable=False)
    before_state = db.Column(db.JSON)
    after_state = db.Column(db.JSON, nullable=False)
    note = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.full_name,
            "action": self.action,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    resource_type = db.Column(db.String(40), nullable=False)
    resource_id = db.Column(db.String(36))
    details = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.full_name,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }


class Feedback(db.Model):
    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("complaint_id", "user_id", name="uq_feedback_complaint_user"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(1000), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class BackupRecord(db.Model):
    __tablename__ = "backup_records"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    operation = db.Column(db.String(20), nullable=False, default="BACKUP")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.full_name,
            "filename": self.filename,
            "operation": self.operation,
            "created_at": self.created_at.isoformat(),
        }


class RollbackRecord(db.Model):
    __tablename__ = "rollback_records"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id"), nullable=False)
    actor_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    history_id = db.Column(db.String(36), db.ForeignKey("complaint_history.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class ComplaintEmbedding(db.Model):
    __tablename__ = "complaint_embeddings"
    __table_args__ = (
        Index(
            "ix_complaint_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    complaint_id = db.Column(db.String(36), db.ForeignKey("complaints.id", ondelete="CASCADE"), primary_key=True)
    embedding = db.Column(JSON().with_variant(Vector(384), "postgresql"), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    complaint = db.relationship("Complaint", backref=db.backref("embedding_record", uselist=False, cascade="all, delete-orphan"))


class KnowledgeDocumentChunk(db.Model):
    __tablename__ = "knowledge_document_chunks"
    __table_args__ = (
        Index(
            "ix_knowledge_chunks_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    department = db.Column(db.String(30), db.ForeignKey("departments.name"), nullable=False, index=True)
    source = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    embedding = db.Column(JSON().with_variant(Vector(384), "postgresql"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class HistoricalComplaint(db.Model):
    __tablename__ = "historical_complaints"
    __table_args__ = (
        Index(
            "ix_historical_complaints_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    source_id = db.Column(db.Integer, unique=True, nullable=False)
    complaint_text = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(30), db.ForeignKey("departments.name"), nullable=False, index=True)
    category_id = db.Column(db.String(36), db.ForeignKey("categories.id"), nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    resolution = db.Column(db.Text, nullable=False, default="")
    embedding = db.Column(JSON().with_variant(Vector(384), "postgresql"))
    category_record = db.relationship("Category")
