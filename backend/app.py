import logging
import os
import shutil
import sqlite3
import csv
from datetime import timedelta
from functools import wraps
from pathlib import Path
from uuid import uuid4

from authlib.integrations.flask_client import OAuth
from flask import Flask, abort, g, jsonify, redirect, request, send_file, url_for
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import func, text
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

from backend.ai_service import (
    analyze_complaint,
    generate_embedding,
    generate_embeddings,
    generate_external_resolution,
)
from backend.models import (
    AuditLog,
    BackupRecord,
    Category,
    Complaint,
    ComplaintEmbedding,
    ComplaintHistory,
    Department,
    Feedback,
    HistoricalComplaint,
    KnowledgeDocumentChunk,
    Permission,
    Role,
    RollbackRecord,
    User,
    db,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPARTMENT_INFO = {
    "TECHNICAL": "IT support, software, internet and equipment",
    "FINANCE": "Fees, payments, refunds and financial aid",
    "ELECTRICAL": "Lighting, wiring, power and electrical equipment",
    "PLUMBING": "Water leakage, supply and blocked drains",
    "SECURITY": "Lost property, access and safety incidents",
}

PERMISSIONS = {
    "CITIZEN": {
        "complaint:create",
        "complaint:read_own",
        "complaint:reopen_own",
        "feedback:create",
    },
    "OFFICER": {
        "complaint:read_own",
        "complaint:read_department",
        "complaint:update_department",
    },
    "ADMIN": {
        "complaint:read_all",
        "complaint:read_own",
        "complaint:read_department",
        "complaint:close",
        "complaint:change_priority",
        "complaint:read_similar",
        "users:manage",
        "audit:read",
        "backup:manage",
        "complaint:rollback",
    },
}

HISTORY_FIELDS = ("status", "department", "category_id", "priority", "assigned_to_id", "resolution")


def _record_audit(actor, action, resource_type, resource_id=None, details=None):
    db.session.add(AuditLog(
        actor_id=actor.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    ))


def _history_state(complaint):
    return {field: getattr(complaint, field) for field in HISTORY_FIELDS}


def _record_history(complaint, actor, action, before_state=None, note=""):
    db.session.add(ComplaintHistory(
        complaint_id=complaint.id,
        actor_id=actor.id,
        action=action,
        before_state=before_state,
        after_state=_history_state(complaint),
        note=note,
    ))


def _persist_knowledge_embeddings():
    chunks = KnowledgeDocumentChunk.query.filter(KnowledgeDocumentChunk.embedding.is_(None)).all()
    vectors = generate_embeddings([chunk.content for chunk in chunks])
    for chunk, embedding in zip(chunks, vectors):
        chunk.embedding = embedding


def _persist_historical_embeddings():
    complaints = HistoricalComplaint.query.filter(HistoricalComplaint.embedding.is_(None)).all()
    vectors = generate_embeddings([item.complaint_text for item in complaints])
    for complaint, embedding in zip(complaints, vectors):
        complaint.embedding = embedding


def _cosine_similarity(left, right):
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def _nearest_database_rows(model, table_name, vector, limit=5, department=None):
    if db.engine.dialect.name == "postgresql":
        key_column = "complaint_id" if table_name == "complaint_embeddings" else "id"
        active_filter = (
            " AND c.status NOT IN ('RESOLVED', 'CLOSED')"
            if table_name == "complaint_embeddings"
            else ""
        )
        join_clause = (
            " JOIN complaints c ON c.id = embeddings.complaint_id"
            if table_name == "complaint_embeddings"
            else ""
        )
        source_table = f"{table_name} embeddings"
        department_filter = " AND embeddings.department = :department" if department else ""
        parameters = {"query_vector": str(vector), "limit": limit}
        if department:
            parameters["department"] = department
        rows = db.session.execute(
            text(
                f"SELECT embeddings.{key_column} AS record_id, embeddings.embedding <=> CAST(:query_vector AS vector) AS distance "
                f"FROM {source_table}{join_clause} WHERE embeddings.embedding IS NOT NULL{active_filter}{department_filter} "
                "ORDER BY embeddings.embedding <=> CAST(:query_vector AS vector) LIMIT :limit"
            ),
            parameters,
        ).all()
        return [(row.record_id, max(0.0, 1.0 - float(row.distance))) for row in rows]

    query = model.query.filter(model.embedding.is_not(None))
    if department:
        query = query.filter(model.department == department)
    if table_name == "complaint_embeddings":
        query = query.join(Complaint).filter(Complaint.status.notin_(("RESOLVED", "CLOSED")))
    items = query.all()
    ranked = []
    for item in items:
        score = _cosine_similarity(vector, item.embedding)
        ranked.append((item.id if hasattr(item, "id") else item.complaint_id, score))
    return sorted(ranked, key=lambda item: item[1], reverse=True)[:limit]


def _apply_database_ai_context(result, embedding):
    if not embedding:
        result["embedding_available"] = False
        return
    result["embedding_available"] = True
    result["live_duplicate"] = False
    complaint_matches = _nearest_database_rows(ComplaintEmbedding, "complaint_embeddings", embedding)
    if complaint_matches:
        result["live_duplicate"] = complaint_matches[0][1] >= 0.78
        result["duplicate"] = result["duplicate"] or result["live_duplicate"]
        result["related_active_reports"] = sum(score >= 0.55 for _, score in complaint_matches)
    historical_matches = _nearest_database_rows(
        HistoricalComplaint,
        "historical_complaints",
        embedding,
        limit=5,
        department=result["department"],
    )
    if historical_matches:
        history_ids = [item_id for item_id, _ in historical_matches]
        history_scores = dict(historical_matches)
        historical = HistoricalComplaint.query.filter(HistoricalComplaint.id.in_(history_ids)).all()
        historical.sort(key=lambda item: history_scores[item.id], reverse=True)
        result["similar_complaints"] = [
            {
                "complaint_id": item.source_id,
                "complaint_text": item.complaint_text,
                "department": item.department,
                "category": item.category_record.name,
                "priority": item.priority,
                "resolution": item.resolution,
                "similarity": round(history_scores[item.id], 4),
            }
            for item in historical
        ]
    knowledge_matches = _nearest_database_rows(
        KnowledgeDocumentChunk,
        "knowledge_document_chunks",
        embedding,
        limit=3,
        department=result["department"],
    )
    if knowledge_matches:
        chunk_ids = [item_id for item_id, _ in knowledge_matches]
        scores = dict(knowledge_matches)
        chunks = KnowledgeDocumentChunk.query.filter(KnowledgeDocumentChunk.id.in_(chunk_ids)).all()
        chunks.sort(key=lambda chunk: scores[chunk.id], reverse=True)
        result["knowledge_documents"] = [
            {"source": chunk.source, "similarity": round(scores[chunk.id], 4)}
            for chunk in chunks
        ]
        first = chunks[0]
        first_guidance = next((line.strip() for line in first.content.splitlines() if line.strip()), "")
        if first_guidance:
            result["suggested_resolution"] += f" Retrieved department guidance: {first_guidance}"


def _seed_reference_data():
    permission_rows = {item.name: item for item in Permission.query.all()}
    for names in PERMISSIONS.values():
        for name in names:
            if name not in permission_rows:
                permission_rows[name] = Permission(name=name)
                db.session.add(permission_rows[name])
    role_rows = {item.name: item for item in Role.query.all()}
    for role_name, permission_names in PERMISSIONS.items():
        role = role_rows.get(role_name)
        if role is None:
            role = Role(name=role_name)
            db.session.add(role)
            role_rows[role_name] = role
        role.permissions = [permission_rows[name] for name in sorted(permission_names)]
    existing_departments = {item.name for item in Department.query.all()}
    for name, description in DEPARTMENT_INFO.items():
        if name not in existing_departments:
            db.session.add(Department(name=name, description=description))
    knowledge_path = PROJECT_ROOT / "data" / "knowledge_base"
    existing_documents = {
        (item.department, item.source)
        for item in KnowledgeDocumentChunk.query.with_entities(
            KnowledgeDocumentChunk.department, KnowledgeDocumentChunk.source
        ).all()
    }
    for department in DEPARTMENT_INFO:
        source_name = department.lower() + ".txt"
        path = knowledge_path / source_name
        if path.exists() and (department, source_name) not in existing_documents:
            content = path.read_text(encoding="utf-8").strip()
            if content:
                db.session.add(KnowledgeDocumentChunk(
                    department=department,
                    source=source_name,
                    content=content,
                ))
    with (PROJECT_ROOT / "data" / "complaints.csv").open(encoding="utf-8-sig", newline="") as source:
        historical_rows = list(csv.DictReader(source))
        for row in historical_rows:
            department = row["department"].upper()
            name = row["category"].strip()
            if not Category.query.filter_by(department=department, name=name).first():
                db.session.add(Category(department=department, name=name))
    db.session.flush()
    existing_source_ids = {
        item.source_id
        for item in HistoricalComplaint.query.with_entities(HistoricalComplaint.source_id).all()
    }
    for row in historical_rows:
        source_id = int(row["complaint_id"])
        if source_id in existing_source_ids:
            continue
        department = row["department"].upper()
        category = Category.query.filter_by(department=department, name=row["category"].strip()).one()
        db.session.add(HistoricalComplaint(
            source_id=source_id,
            complaint_text=row["complaint_text"],
            department=department,
            category_record=category,
            priority=row["priority"].upper(),
            resolution=row["resolution"],
        ))
    db.session.commit()


def _user_for_identity():
    user = db.session.get(User, get_jwt_identity())
    if user is None or not user.is_active:
        abort(401, description="Your account is unavailable.")
    return user


def _permission_required(permission):
    def decorator(handler):
        @wraps(handler)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user = _user_for_identity()
            if permission not in {item.name for item in user.role.permissions}:
                abort(403, description="You do not have permission to perform this action.")
            g.user = user
            return handler(*args, **kwargs)
        return wrapped
    return decorator


def _can_view(user, complaint):
    if user.role.name == "ADMIN":
        return True
    if user.role.name == "OFFICER":
        return bool(user.department and user.department == complaint.department)
    return user.id == complaint.reporter_id


def _complaint_or_404(complaint_id):
    complaint = db.session.get(Complaint, complaint_id)
    if complaint is None or not _can_view(g.user, complaint):
        abort(404, description="Complaint not found.")
    return complaint


def _json_object():
    if not request.is_json:
        abort(400, description="Send a JSON request body.")
    value = request.get_json(silent=False)
    if not isinstance(value, dict):
        abort(400, description="The request body must be a JSON object.")
    return value


def _error_response(error):
    return jsonify({"error": error.description}), error.code


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    load_dotenv(PROJECT_ROOT / ".env")
    os.makedirs(app.instance_path, exist_ok=True)
    backup_dir = Path(os.getenv("BACKUP_DIR", app.instance_path + os.sep + "backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key and os.getenv("APP_ENV", "development").lower() == "production":
        raise RuntimeError("SECRET_KEY must be configured in production.")
    app.config.update(
        SECRET_KEY=secret_key or "development-only-change-this-secret",
        
        SQLALCHEMY_DATABASE_URI=(
            os.getenv(
                "DATABASE_URL",
                "sqlite:///" + str(Path(app.instance_path) / "complaints.db").replace("\\", "/"),
            )
            .replace("postgres://", "postgresql+psycopg2://", 1)
            .replace("postgresql://", "postgresql+psycopg2://", 1)
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        APP_ENV=os.getenv("APP_ENV", "development").lower(),
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", secret_key or "development-only-change-this-jwt-secret"),
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_ACCESS_COOKIE_NAME="access_token_cookie",
        JWT_ACCESS_COOKIE_PATH="/api/",
        JWT_COOKIE_CSRF_PROTECT=True,
        JWT_CSRF_IN_COOKIES=True,
        JWT_CSRF_METHODS=["POST", "PUT", "PATCH", "DELETE"],
        JWT_COOKIE_SAMESITE=os.getenv("JWT_COOKIE_SAMESITE", "Lax"),
        JWT_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        JWT_ACCESS_CSRF_COOKIE_PATH="/",
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=8),
        MAX_CONTENT_LENGTH=65536,
        GOOGLE_CLIENT_ID=os.getenv("GOOGLE_CLIENT_ID"),
        GOOGLE_CLIENT_SECRET=os.getenv("GOOGLE_CLIENT_SECRET"),
        ENABLE_GEMINI=os.getenv("ENABLE_GEMINI", "false").lower() == "true",
        FRONTEND_URL=os.getenv("FRONTEND_URL", "http://localhost:5173"),
        BACKUP_DIR=str(backup_dir.resolve()),
    )
    if test_config:
        app.config.update(test_config)
    if app.config.get("APP_ENV") == "production":
        jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        if not secret_key or len(secret_key) < 32 or secret_key.startswith("replace-"):
            raise RuntimeError("Set SECRET_KEY to a unique random value of at least 32 characters in production.")
        if not jwt_secret or len(jwt_secret) < 32 or jwt_secret.startswith("replace-"):
            raise RuntimeError("Set JWT_SECRET_KEY to a different unique random value of at least 32 characters in production.")
    if app.config.get("APP_ENV") == "production" and not app.config["JWT_COOKIE_SECURE"]:
        raise RuntimeError("COOKIE_SECURE=true is required in production.")
    if bool(app.config["GOOGLE_CLIENT_ID"]) != bool(app.config["GOOGLE_CLIENT_SECRET"]):
        raise RuntimeError("Configure both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or leave both empty.")
    if app.config["ENABLE_GEMINI"] and not os.getenv("GEMINI_API_KEY", "").strip():
        raise RuntimeError("GEMINI_API_KEY is required when ENABLE_GEMINI=true.")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app)
    JWTManager(app)
    CORS(
        app,
        supports_credentials=True,
        origins=[app.config["FRONTEND_URL"]],
        allow_headers=["Content-Type", "X-CSRF-TOKEN"],
    )
    app.register_error_handler(400, _error_response)
    app.register_error_handler(401, _error_response)
    app.register_error_handler(403, _error_response)
    app.register_error_handler(404, _error_response)
    app.register_error_handler(409, _error_response)
    app.register_error_handler(413, _error_response)
    app.register_error_handler(422, _error_response)

    oauth = None
    if app.config["GOOGLE_CLIENT_ID"] and app.config["GOOGLE_CLIENT_SECRET"]:
        oauth = OAuth(app)
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    with app.app_context():
        if db.engine.dialect.name == "postgresql":
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.session.commit()
        db.create_all()
        _seed_reference_data()

    @app.get("/api/v1/health")
    def health():
        return jsonify({"status": "ok", "service": "smart-complaint-routing"})

    @app.get("/api/v1/auth/options")
    def auth_options():
        return jsonify({
            "google_enabled": oauth is not None,
            "external_ai_enabled": app.config["ENABLE_GEMINI"],
        })

    @app.post("/api/v1/auth/register")
    def register():
        body = _json_object()
        if not isinstance(body.get("email"), str) or not isinstance(body.get("full_name"), str):
            abort(400, description="Enter your name and email address.")
        email = body["email"].strip().lower()
        full_name = body["full_name"].strip()
        password = body.get("password", "")
        user_type = str(body.get("user_type", "STUDENT")).upper()
        allowed_types = {"STUDENT", "FACULTY", "WORKING_STAFF"}
        if len(full_name) < 2 or len(full_name) > 120:
            abort(400, description="Name must contain 2 to 120 characters.")
        if "@" not in email or len(email) > 254:
            abort(400, description="Enter a valid email address.")
        if not isinstance(password, str) or len(password) < 10 or len(password) > 128:
            abort(400, description="Password must contain 10 to 128 characters.")
        if user_type not in allowed_types:
            abort(400, description="Choose Student, Faculty, or Working Staff.")
        if User.query.filter_by(email=email).first():
            abort(409, description="An account with that email already exists.")
        citizen_role = Role.query.filter_by(name="CITIZEN").one()
        user = User(
            email=email,
            full_name=full_name,
            password_hash=generate_password_hash(password, method="scrypt"),
            user_type=user_type,
            role=citizen_role,
        )
        db.session.add(user)
        db.session.flush()
        _record_audit(user, "ACCOUNT_REGISTERED", "user", user.id)
        db.session.commit()
        response = jsonify({"user": user.to_dict()})
        response.status_code = 201
        set_access_cookies(response, create_access_token(identity=user.id))
        return response

    @app.post("/api/v1/auth/login")
    def login():
        body = _json_object()
        email = str(body.get("email", "")).strip().lower()
        password = body.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user is None or not user.is_active or not user.password_hash or not check_password_hash(user.password_hash, password if isinstance(password, str) else ""):
            abort(401, description="Email or password is incorrect.")
        response = jsonify({"user": user.to_dict()})
        set_access_cookies(response, create_access_token(identity=user.id))
        return response

    @app.get("/api/v1/auth/me")
    @jwt_required()
    def me():
        return jsonify({"user": _user_for_identity().to_dict()})

    @app.get("/api/v1/auth/csrf")
    @jwt_required()
    def csrf_token():
        # Safe GET endpoint: return the CSRF claim from the current access JWT.
        # The frontend cannot read cookies set by the API's separate hostname.
        return jsonify({"csrf_token": get_jwt()["csrf"]})

    @app.post("/api/v1/auth/logout")
    @jwt_required()
    def logout():
        _user_for_identity()
        response = jsonify({"message": "Signed out."})
        unset_jwt_cookies(response)
        return response

    @app.get("/api/v1/auth/google")
    def google_login():
        if oauth is None:
            abort(503, description="Google sign-in is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
        callback = url_for("google_callback", _external=True)
        return oauth.google.authorize_redirect(callback)

    
    @app.get("/api/v1/auth/google/callback")
    def google_callback():
        if oauth is None:
            abort(503, description="Google sign-in is not configured.")

        token = oauth.google.authorize_access_token()
        profile = token.get("userinfo")

        if not profile:
            profile = oauth.google.get(
                "https://openidconnect.googleapis.com/v1/userinfo"
            ).json()

        email = str(profile.get("email", "")).strip().lower()
        subject = profile.get("sub")

        if not subject or not email or not profile.get("email_verified"):
            abort(401, description="Google did not return a verified email address.")

        # Find an account already linked to this Google identity.
        user = User.query.filter_by(google_subject=subject).first()

        # If not linked, check whether this email already has an account.
        if user is None:
            user = User.query.filter_by(email=email).first()

        # Create a new account when this Google email is not registered.
        if user is None:
            citizen_role = Role.query.filter_by(name="CITIZEN").one()

            user = User(
                email=email,
                full_name=str(profile.get("name") or email.split("@")[0])[:120],
                user_type="STUDENT",
                role=citizen_role,
                google_subject=subject,
                is_active=True,
            )
            db.session.add(user)
            db.session.flush()

            _record_audit(user, "GOOGLE_SIGN_IN", "user", user.id)

        else:
            # Do not allow a disabled existing account to sign in.
            if not user.is_active:
                db.session.rollback()
                abort(403, description="This account is disabled.")

            # Prevent linking an account to a different Google identity.
            if user.google_subject and user.google_subject != subject:
                abort(
                    409,
                    description="That account is already linked to another Google identity.",
                )

            user.google_subject = subject
            db.session.flush()

            _record_audit(user, "GOOGLE_SIGN_IN", "user", user.id)

        db.session.commit()

        response = redirect(app.config["FRONTEND_URL"])
        set_access_cookies(response, create_access_token(identity=user.id))
        return response

    @app.post("/api/v1/ai/analyze")
    @_permission_required("complaint:create")
    def analyze():
        body = _json_object()
        text = str(body.get("description", "")).strip()
        if len(text) < 15 or len(text) > 5000:
            abort(400, description="Describe the issue in 15 to 5,000 characters.")
        requested_department = str(body.get("department", "")).upper()
        if requested_department and requested_department not in DEPARTMENT_INFO:
            abort(400, description="Choose one of the five supported departments.")
        result = analyze_complaint(text, requested_department or None)
        embedding = generate_embedding(text)
        _persist_knowledge_embeddings()
        _persist_historical_embeddings()
        _apply_database_ai_context(result, embedding)
        result["external_ai_available"] = app.config["ENABLE_GEMINI"]
        db.session.commit()
        result.pop("embedding", None)
        return jsonify(result)

    @app.get("/api/v1/departments")
    @_permission_required("complaint:read_own")
    def departments():
        items = Department.query.order_by(Department.name).all()
        return jsonify({"departments": [{"name": item.name, "description": item.description} for item in items]})

    @app.get("/api/v1/complaints")
    @_permission_required("complaint:read_own")
    def list_complaints():
        query = Complaint.query
        if g.user.role.name == "CITIZEN":
            query = query.filter_by(reporter_id=g.user.id)
        elif g.user.role.name == "OFFICER":
            if not g.user.department:
                return jsonify({"complaints": []})
            query = query.filter_by(department=g.user.department)
        status = request.args.get("status")
        if status:
            query = query.filter_by(status=status.upper())
        items = query.order_by(Complaint.created_at.desc()).limit(200).all()
        return jsonify({"complaints": [item.to_dict(include_description=False) for item in items]})

    @app.post("/api/v1/complaints")
    @_permission_required("complaint:create")
    def create_complaint():
        body = _json_object()
        title = str(body.get("title", "")).strip()
        description = str(body.get("description", "")).strip()
        location = str(body.get("location", "")).strip()
        if len(title) < 4 or len(title) > 160:
            abort(400, description="Title must contain 4 to 160 characters.")
        if len(description) < 15 or len(description) > 5000:
            abort(400, description="Description must contain 15 to 5,000 characters.")
        if len(location) > 160:
            abort(400, description="Location must be at most 160 characters.")
        allow_external_ai = body.get("allow_external_ai", False)
        if not isinstance(allow_external_ai, bool):
            abort(400, description="allow_external_ai must be true or false.")
        if allow_external_ai and not app.config["ENABLE_GEMINI"]:
            abort(400, description="External AI generation is not enabled.")
        requested_department = str(body.get("department", "")).upper()
        if requested_department and requested_department not in DEPARTMENT_INFO:
            abort(400, description="Choose one of the five supported departments.")
        ai_result = analyze_complaint(description, requested_department or None)
        embedding = generate_embedding(description)
        _persist_knowledge_embeddings()
        _persist_historical_embeddings()
        _apply_database_ai_context(ai_result, embedding)
        requested_department = requested_department or ai_result["department"]
        ai_result["external_ai_used"] = False
        if allow_external_ai:
            external_resolution, external_warning = generate_external_resolution(description, ai_result)
            if external_resolution:
                ai_result["suggested_resolution"] = external_resolution
                ai_result["model"] = "gemini"
                ai_result["external_ai_used"] = True
            if external_warning:
                ai_result["warning"] = external_warning
        complaint = Complaint(
            reference="CMP-" + uuid4().hex[:8].upper(),
            reporter_id=g.user.id,
            title=title,
            description=description,
            location=location,
            department=requested_department,
            category_record=Category.query.filter_by(
                department=requested_department,
                name=ai_result["category"],
            ).first() or Category(department=requested_department, name=ai_result["category"]),
            priority=ai_result["priority"],
            status="SUBMITTED",
            suggested_resolution=ai_result["suggested_resolution"],
            ai_metadata=ai_result,
        )
        db.session.add(complaint)
        db.session.flush()
        if embedding:
            db.session.add(ComplaintEmbedding(
                complaint_id=complaint.id,
                embedding=embedding,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
            ))
        _persist_knowledge_embeddings()
        _record_history(complaint, g.user, "SUBMITTED", note="Complaint submitted.")
        _record_audit(g.user, "COMPLAINT_SUBMITTED", "complaint", complaint.id, {
            "reference": complaint.reference,
            "external_ai_used": ai_result["external_ai_used"],
        })
        db.session.commit()
        return jsonify({"complaint": complaint.to_dict()}), 201

    @app.get("/api/v1/complaints/<complaint_id>")
    @_permission_required("complaint:read_own")
    def get_complaint(complaint_id):
        complaint = _complaint_or_404(complaint_id)
        payload = complaint.to_dict()
        if complaint.reporter_id == g.user.id:
            payload["feedback_submitted"] = Feedback.query.filter_by(
                complaint_id=complaint.id,
                user_id=g.user.id,
            ).first() is not None
        return jsonify({"complaint": payload})

    @app.get("/api/v1/complaints/<complaint_id>/history")
    @_permission_required("complaint:read_own")
    def complaint_history(complaint_id):
        complaint = _complaint_or_404(complaint_id)
        items = ComplaintHistory.query.filter_by(complaint_id=complaint.id).order_by(
            ComplaintHistory.created_at.asc(),
            ComplaintHistory.id.asc(),
        ).all()
        return jsonify({"history": [item.to_dict() for item in items]})

    @app.patch("/api/v1/complaints/<complaint_id>/transfer")
    @_permission_required("complaint:update_department")
    def transfer_complaint(complaint_id):
        complaint = _complaint_or_404(complaint_id)

        if g.user.role.name != "OFFICER":
            abort(403, description="Only officers can transfer complaints.")

        if not g.user.department or g.user.department != complaint.department:
            abort(403, description="You can only transfer complaints in your department.")

        body = _json_object()
        destination = str(body.get("department", "")).strip().upper()
        reason = str(body.get("reason", "")).strip()

        if not destination:
            abort(400, description="Destination department is required.")

        if len(reason) < 10:
            abort(400, description="Transfer reason must be at least 10 characters.")

        if destination == complaint.department:
            abort(400, description="Choose a different destination department.")

        target_department = Department.query.filter_by(name=destination).first()
        if target_department is None:
            abort(400, description="Destination department does not exist.")

        before = _history_state(complaint)
        old_department = complaint.department

        complaint.department = destination
        complaint.assigned_to_id = None

        _record_history(
            complaint,
            g.user,
            "DEPARTMENT_TRANSFERRED",
            before,
            f"Transferred from {old_department} to {destination}. Reason: {reason}",
        )

        _record_audit(
            g.user,
            "COMPLAINT_DEPARTMENT_TRANSFERRED",
            "complaint",
            complaint.id,
            {
                "old_department": old_department,
                "new_department": destination,
                "reason": reason,
            },
        )

        db.session.commit()
        return jsonify({"complaint": complaint.to_dict()})

    @app.patch("/api/v1/complaints/<complaint_id>/status")
    @_permission_required("complaint:read_own")
        
    def update_status(complaint_id):
        complaint = _complaint_or_404(complaint_id)
        
        role = g.user.role.name
        if role == "OFFICER":
            if not g.user.department or g.user.department != complaint.department:
                abort(403, description="You can only update complaints in your department.")
                
        elif role != "ADMIN":
            abort(403, description="You are not allowed to update complaint status.")
        
        body = _json_object()
        
        new_status = str(body.get("status", "")).upper()
        note = str(body.get("note", "")).strip()
        resolution = str(body.get("resolution", "")).strip()
        
        if g.user.role.name == "ADMIN":
            if new_status != "CLOSED":
                abort(403, description="Admins may only close resolved complaints.")
                
        else:
            if new_status not in {"IN_PROGRESS", "RESOLVED"}:
                abort(403, description="Officers may only start or resolve complaints.")
        
        allowed_transitions = {
            "SUBMITTED": {"IN_PROGRESS"},
            "REOPENED": {"IN_PROGRESS"},
            "IN_PROGRESS": {"RESOLVED"},
            "RESOLVED": {"CLOSED"},
            "CLOSED": set(),
        }
        if new_status not in allowed_transitions.get(complaint.status, set()):
            abort(409, description=f"A complaint in {complaint.status.replace('_', ' ').title()} cannot move to {new_status.replace('_', ' ').title()}.")
        if new_status == "RESOLVED" and len(resolution) < 10:
            abort(400, description="Enter at least 10 characters describing the resolution.")
        before = _history_state(complaint)
        complaint.status = new_status
        if resolution:
            complaint.resolution = resolution[:5000]
        _record_history(complaint, g.user, "STATUS_UPDATED", before, note[:500])
        _record_audit(g.user, "COMPLAINT_STATUS_UPDATED", "complaint", complaint.id, {"status": new_status})
        db.session.commit()
        return jsonify({"complaint": complaint.to_dict()})

    @app.post("/api/v1/complaints/<complaint_id>/reopen")
    @_permission_required("complaint:reopen_own")
    def reopen_complaint(complaint_id):
        complaint = _complaint_or_404(complaint_id)
        if complaint.reporter_id != g.user.id or complaint.status not in {"RESOLVED", "CLOSED"}:
            abort(403, description="Only the reporting citizen may reopen a resolved or closed complaint.")
        before = _history_state(complaint)
        complaint.status = "REOPENED"
        _record_history(complaint, g.user, "COMPLAINT_REOPENED", before, "Reporter requested further assistance.")
        _record_audit(g.user, "COMPLAINT_REOPENED", "complaint", complaint.id)
        db.session.commit()
        return jsonify({"complaint": complaint.to_dict()})

    @app.post("/api/v1/complaints/<complaint_id>/feedback")
    @_permission_required("feedback:create")
    def submit_feedback(complaint_id):
        complaint = _complaint_or_404(complaint_id)
        if complaint.reporter_id != g.user.id or complaint.status not in {"RESOLVED", "CLOSED"}:
            abort(403, description="Feedback is available to the reporter after resolution.")
        body = _json_object()
        rating = body.get("rating")
        if not isinstance(rating, int) or isinstance(rating, bool) or rating < 1 or rating > 5:
            abort(400, description="Rating must be an integer from 1 to 5.")
        if Feedback.query.filter_by(complaint_id=complaint.id, user_id=g.user.id).first():
            abort(409, description="Feedback has already been submitted.")
        feedback = Feedback(
            complaint_id=complaint.id,
            user_id=g.user.id,
            rating=rating,
            comment=str(body.get("comment", "")).strip()[:1000],
        )
        db.session.add(feedback)
        _record_audit(g.user, "FEEDBACK_SUBMITTED", "complaint", complaint.id, {"rating": rating})
        db.session.commit()
        return jsonify({"message": "Feedback recorded."}), 201

    @app.get("/api/v1/dashboard")
    @_permission_required("complaint:read_own")
    def dashboard():
        query = Complaint.query
        if g.user.role.name == "CITIZEN":
            query = query.filter_by(reporter_id=g.user.id)
        elif g.user.role.name == "OFFICER":
            query = query.filter_by(department=g.user.department) if g.user.department else query.filter_by(id="")
        total = query.count()
        status_rows = query.with_entities(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all()
        department_rows = query.with_entities(Complaint.department, func.count(Complaint.id)).group_by(Complaint.department).all()
        return jsonify({
            "total": total,
            "by_status": {status: count for status, count in status_rows},
            "by_department": {department: count for department, count in department_rows},
        })

    @app.get("/api/v1/admin/users")
    @_permission_required("users:manage")
    def admin_users():
        users = User.query.order_by(User.created_at.desc()).limit(500).all()
        return jsonify({"users": [user.to_dict() for user in users]})

    @app.get("/api/v1/admin/categories")
    @_permission_required("users:manage")
    def admin_categories():
        items = Category.query.order_by(Category.department, Category.name).all()
        return jsonify({"categories": [{"id": item.id, "department": item.department, "name": item.name} for item in items]})

    @app.post("/api/v1/admin/categories")
    @_permission_required("users:manage")
    def create_category():
        body = _json_object()
        department = str(body.get("department", "")).upper()
        name = str(body.get("name", "")).strip()
        if department not in DEPARTMENT_INFO or len(name) < 2 or len(name) > 80:
            abort(400, description="Choose a supported department and a category name of 2 to 80 characters.")
        if Category.query.filter_by(department=department, name=name).first():
            abort(409, description="That category already exists for this department.")
        category = Category(department=department, name=name)
        db.session.add(category)
        db.session.flush()
        _record_audit(g.user, "CATEGORY_CREATED", "category", category.id, {"department": department, "name": name})
        db.session.commit()
        return jsonify({"category": {"id": category.id, "department": department, "name": name}}), 201

    @app.patch("/api/v1/admin/users/<user_id>/role")
    @_permission_required("users:manage")
    def update_user_role(user_id):
        target = db.session.get(User, user_id)
        if target is None:
            abort(404, description="User not found.")
        body = _json_object()
        role_name = str(body.get("role", "")).upper()
        if role_name not in {"CITIZEN", "OFFICER", "ADMIN"}:
            abort(400, description="Role must be Citizen, Officer, or Admin.")
        if target.id == g.user.id and role_name != "ADMIN":
            abort(400, description="You cannot remove your own administrator access.")
        department = str(body.get("department", "")).upper()
        if role_name == "OFFICER" and department not in DEPARTMENT_INFO:
            abort(400, description="Choose a department for this officer.")
        before_role = target.role.name
        target.role = Role.query.filter_by(name=role_name).one()
        target.department = department if role_name == "OFFICER" else None
        _record_audit(g.user, "USER_ROLE_UPDATED", "user", target.id, {"from": before_role, "to": role_name})
        db.session.commit()
        return jsonify({"user": target.to_dict()})

    @app.patch("/api/v1/admin/users/<user_id>/active")
    @_permission_required("users:manage")
    def toggle_user(user_id):
        target = db.session.get(User, user_id)
        if target is None:
            abort(404, description="User not found.")
        if target.id == g.user.id:
            abort(400, description="You cannot disable your own account.")
        body = _json_object()
        if not isinstance(body.get("is_active"), bool):
            abort(400, description="is_active must be true or false.")
        target.is_active = body["is_active"]
        _record_audit(g.user, "USER_ACTIVE_STATE_UPDATED", "user", target.id, {"is_active": target.is_active})
        db.session.commit()
        return jsonify({"user": target.to_dict()})

    @app.get("/api/v1/admin/audit")
    @_permission_required("audit:read")
    def audit_logs():
        items = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
        return jsonify({"events": [item.to_dict() for item in items]})

    @app.post("/api/v1/admin/complaints/<complaint_id>/rollback")
    @_permission_required("complaint:rollback")
    def rollback_complaint(complaint_id):
        complaint = db.session.get(Complaint, complaint_id)
        if complaint is None:
            abort(404, description="Complaint not found.")
        body = _json_object()
        history_id = body.get("history_id")
        if not isinstance(history_id, str):
            abort(400, description="history_id must identify a complaint history event.")
        history = db.session.get(ComplaintHistory, history_id)
        if history is None or history.complaint_id != complaint.id or not history.before_state:
            abort(400, description="Choose a reversible history event for this complaint.")
        latest_history = ComplaintHistory.query.filter_by(
            complaint_id=complaint.id
        ).order_by(ComplaintHistory.created_at.desc(), ComplaintHistory.id.desc()).first()
        if latest_history is None or latest_history.id != history.id:
            abort(409, description="Only the latest complaint change can be rolled back.")
        before_rollback = _history_state(complaint)
        for field in HISTORY_FIELDS:
            setattr(complaint, field, history.before_state[field])
        _record_history(complaint, g.user, "ADMIN_ROLLBACK", before_rollback, f"Reversed history event {history.id}.")
        db.session.add(RollbackRecord(
            complaint_id=complaint.id,
            actor_id=g.user.id,
            history_id=history.id,
        ))
        _record_audit(g.user, "COMPLAINT_ROLLED_BACK", "complaint", complaint.id, {"history_id": history.id})
        db.session.commit()
        return jsonify({"complaint": complaint.to_dict()})

    @app.get("/api/v1/admin/backups")
    @_permission_required("backup:manage")
    def list_backups():
        items = BackupRecord.query.order_by(BackupRecord.created_at.desc()).limit(100).all()
        return jsonify({"backups": [item.to_dict() for item in items]})

    @app.post("/api/v1/admin/backups")
    @_permission_required("backup:manage")
    def create_backup():
        database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        if not database_uri.startswith("sqlite:///"):
            abort(501, description="Automated file backups currently support SQLite. Use pg_dump for PostgreSQL deployments.")
        filename = f"complaints-{uuid4().hex[:12]}.sqlite3"
        backup_path = Path(app.config["BACKUP_DIR"]) / filename
        source = db.engine.raw_connection()
        try:
            destination = sqlite3.connect(str(backup_path))
            try:
                source.driver_connection.backup(destination)
            finally:
                destination.close()
        finally:
            source.close()
        record = BackupRecord(actor_id=g.user.id, filename=filename, operation="BACKUP")
        db.session.add(record)
        db.session.flush()
        _record_audit(g.user, "DATABASE_BACKUP_CREATED", "backup", record.id, {"filename": filename})
        db.session.commit()
        return jsonify({"backup": record.to_dict()}), 201

    @app.get("/api/v1/admin/backups/<backup_id>/download")
    @_permission_required("backup:manage")
    def download_backup(backup_id):
        record = db.session.get(BackupRecord, backup_id)
        if record is None:
            abort(404, description="Backup not found.")
        path = Path(app.config["BACKUP_DIR"]) / record.filename
        if not path.is_file():
            abort(404, description="Backup file is no longer available.")
        return send_file(path, as_attachment=True, download_name=record.filename)

    @app.post("/api/v1/admin/backups/<backup_id>/restore")
    @_permission_required("backup:manage")
    def restore_backup(backup_id):
        if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///"):
            abort(501, description="Automated restore currently supports SQLite only.")
        body = _json_object()
        if body.get("confirmation") != "RESTORE":
            abort(400, description='To confirm, send confirmation="RESTORE".')
        record = db.session.get(BackupRecord, backup_id)
        if record is None:
            abort(404, description="Backup not found.")
        backup_path = (Path(app.config["BACKUP_DIR"]) / record.filename).resolve()
        backup_root = Path(app.config["BACKUP_DIR"]).resolve()
        if os.path.commonpath([str(backup_root), str(backup_path)]) != str(backup_root) or not backup_path.is_file():
            abort(404, description="Backup file is unavailable.")
        database_path = Path(db.engine.url.database).resolve()
        pre_restore_name = f"pre-restore-{uuid4().hex[:12]}.sqlite3"
        db.session.commit()
        db.engine.dispose()
        if database_path.exists():
            shutil.copy2(database_path, Path(app.config["BACKUP_DIR"]) / pre_restore_name)
        shutil.copy2(backup_path, database_path)
        db.create_all()
        _seed_reference_data()
        _record_audit(g.user, "DATABASE_RESTORED", "backup", backup_id, {"pre_restore_file": pre_restore_name})
        db.session.add(BackupRecord(actor_id=g.user.id, filename=pre_restore_name, operation="PRE_RESTORE"))
        db.session.commit()
        return jsonify({"message": "Database restored. The pre-restore database was saved as a backup.", "pre_restore_file": pre_restore_name})

    return app


app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
        use_reloader=False,
    )
