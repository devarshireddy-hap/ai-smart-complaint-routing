import logging
import os
import re
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from uuid import uuid4

from authlib.integrations.flask_client import OAuth
from flask import Flask, abort, g, jsonify, redirect, request, send_file, session, url_for
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy import func, inspect, text
from sqlalchemy.engine import make_url
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

from backend.ai_service import (
    analyze_complaint,
    generate_embedding,
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
    "USER": {
        "complaint.create",
        "complaint.read",
        "complaint.reopen",
        "feedback.create",
    },
    "OFFICER": {
        "complaint.read",
        "complaint.update",
        "complaint.assign",
        "complaint.analyze",
        "complaint.resolve",
    },
    "ADMIN": {
        "complaint.create",
        "complaint.read",
        "complaint.update",
        "complaint.delete",
        "complaint.assign",
        "complaint.analyze",
        "complaint.resolve",
        "complaint.reopen",
        "feedback.create",
        "user.read",
        "user.update",
        "user.create",
        "user.delete",
        "department.read",
        "department.manage",
        "category.manage",
        "admin.access",
        "admin.reports",
        "admin.audit",
        "backup.manage",
        "rag.manage",
    },
}

HISTORY_FIELDS = ("status", "department", "category_id", "priority")


def _is_vit_email(email):
    domain = email.rpartition("@")[2]
    return bool(re.fullmatch(r"vit[a-z0-9-]+(?:\.[a-z0-9-]+)*\.ac\.in", domain))


def _normalized_role(role_name):
    return "USER" if role_name == "CITIZEN" else role_name


def _record_audit(actor, action, resource_type, resource_id=None, details=None, old_values=None):
    event = AuditLog(
        actor_id=actor.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        old_values=old_values,
    )
    db.session.add(event)
    return event


def _history_state(complaint):
    return {field: getattr(complaint, field) for field in HISTORY_FIELDS}


def _set_complaint_department(complaint, department):
    previous_category = complaint.category_record
    complaint.department_record = department
    complaint.category_record = (
        Category.query.filter_by(
            department_id=department.id,
            name=previous_category.name,
        ).first()
        if previous_category
        else None
    )


def _record_history(complaint, actor, action, before_state=None, note=""):
    event = ComplaintHistory(
        complaint_id=complaint.id,
        actor_id=actor.id,
        action=action,
        before_state=before_state,
        after_state=_history_state(complaint),
        note=note,
    )
    db.session.add(event)
    return event


def _validate_postgres_schema():
    required_columns = {
        "users": {"user_id", "email", "name", "password_hash", "user_type", "google_id"},
        "roles": {"role_id", "role_name"},
        "permissions": {"permission_id", "permission_name"},
        "role_permissions": {"role_id", "permission_id"},
        "user_roles": {"user_id", "role_id"},
        "departments": {"department_id", "department_name"},
        "categories": {"category_id", "category_name", "department_id"},
        "complaints": {
            "complaint_id", "user_id", "title", "description", "category_id",
            "department_id", "priority", "status", "is_duplicate",
        },
        "complaint_history": {
            "history_id", "complaint_id", "changed_by", "change_type",
            "old_values", "new_values", "change_description", "changed_at",
        },
        "complaint_embeddings": {
            "embedding_id", "complaint_id", "embedding_vector", "embedding_model",
        },
        "knowledge_document_chunks": {
            "chunk_id", "document_id", "department_id", "title", "chunk_text",
            "chunk_index", "chunk_embedding", "embedding_model", "metadata", "is_active",
        },
        "audit_logs": {"log_id", "user_id", "action", "resource_type", "resource_id", "new_values"},
        "backup_records": {"backup_id", "backup_name", "created_by", "backup_type"},
        "rollback_records": {
            "rollback_id", "backup_id", "initiated_by", "status",
            "reversed_history_id", "rollback_history_id",
        },
        "feedback": {"feedback_id", "complaint_id", "user_id", "rating", "comment"},
    }
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    missing_tables = set(required_columns) - tables
    if missing_tables:
        raise RuntimeError(
            "Database schema is incomplete. Initialize it using "
            "database/schema/00_init.sql and database/seeds/01_init_data.sql. "
            f"Missing tables: {', '.join(sorted(missing_tables))}"
        )

    missing_columns = []
    for table, expected_columns in required_columns.items():
        present_columns = {column["name"] for column in inspector.get_columns(table)}
        missing_columns.extend(
            f"{table}.{column}"
            for column in sorted(expected_columns - present_columns)
        )
    if missing_columns:
        raise RuntimeError(
            "Database schema is outdated. Apply the matching database migration; "
            f"missing columns: {', '.join(missing_columns)}"
        )

    with db.engine.connect() as connection:
        vector_extension = connection.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
        if vector_extension is None:
            raise RuntimeError("PostgreSQL pgvector extension 'vector' is not installed.")

        vector_types = connection.execute(text(
            """
            SELECT table_name, column_name, format_type(a.atttypid, a.atttypmod) AS vector_type
            FROM (VALUES
                ('complaint_embeddings', 'embedding_vector'),
                ('knowledge_document_chunks', 'chunk_embedding')
            ) AS expected(table_name, column_name)
            JOIN pg_class c ON c.relname = expected.table_name
            JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = current_schema()
            JOIN pg_attribute a ON a.attrelid = c.oid
                AND a.attname = expected.column_name
                AND NOT a.attisdropped
            """
        )).mappings().all()
        actual_vector_types = {
            (row["table_name"], row["column_name"]): row["vector_type"]
            for row in vector_types
        }
        expected_vectors = {
            ("complaint_embeddings", "embedding_vector"),
            ("knowledge_document_chunks", "chunk_embedding"),
        }
        if set(actual_vector_types) != expected_vectors or any(
            vector_type != "vector(384)" for vector_type in actual_vector_types.values()
        ):
            raise RuntimeError(
                "Database vector columns must be complaint_embeddings.embedding_vector "
                "and knowledge_document_chunks.chunk_embedding, both vector(384)."
            )

        index_definitions = connection.execute(text(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = current_schema()
              AND tablename IN ('complaint_embeddings', 'knowledge_document_chunks')
            """
        )).mappings().all()
    expected_indexes = {
        "idx_complaint_embeddings_vector": ("embedding_vector", "vector_cosine_ops"),
        "idx_knowledge_chunks_embedding": ("chunk_embedding", "vector_cosine_ops"),
    }
    for index_name, fragments in expected_indexes.items():
        definition = next(
            (row["indexdef"].lower() for row in index_definitions if row["indexname"] == index_name),
            "",
        )
        if not definition or any(fragment not in definition for fragment in fragments):
            raise RuntimeError(
                f"Missing or incorrect cosine HNSW vector index: {index_name}."
            )

    required_roles = {"ADMIN", "OFFICER", "USER"}
    roles = {role.name for role in Role.query.all()}
    if not required_roles.issubset(roles):
        raise RuntimeError(
            "Database role seed is incomplete. Load database/seeds/01_init_data.sql."
        )
    required_departments = set(DEPARTMENT_INFO)
    departments = {department.name for department in Department.query.all()}
    if not required_departments.issubset(departments):
        raise RuntimeError(
            "Database department seed is incomplete. Load database/seeds/01_init_data.sql."
        )


def _apply_database_ai_context(result, embedding):
    if not embedding or db.engine.dialect.name != "postgresql":
        result["embedding_available"] = False
        return
    result["embedding_available"] = True
    result["live_duplicate"] = False
    query_vector = "[" + ",".join(str(float(value)) for value in embedding) + "]"
    complaint_matches = db.session.execute(
        text(
            """
            SELECT c.complaint_id AS record_id,
                   1 - (ce.embedding_vector <=> CAST(:query_vector AS vector)) AS similarity
            FROM complaint_embeddings AS ce
            JOIN complaints AS c ON c.complaint_id = ce.complaint_id
            WHERE ce.embedding_vector IS NOT NULL
              AND c.status NOT IN ('RESOLVED', 'REJECTED')
              AND COALESCE(c.is_duplicate, FALSE) = FALSE
            ORDER BY ce.embedding_vector <=> CAST(:query_vector AS vector)
            LIMIT 5
            """
        ),
        {"query_vector": query_vector},
    ).all()
    if complaint_matches:
        result["live_duplicate"] = float(complaint_matches[0].similarity) >= 0.78
        result["duplicate"] = result["duplicate"] or result["live_duplicate"]
        result["related_active_reports"] = sum(
            float(row.similarity) >= 0.55 for row in complaint_matches
        )

    historical = db.session.execute(
        text(
            """
            SELECT c.complaint_id, c.title, c.description, d.department_name AS department,
                   cat.category_name AS category, c.priority, c.status,
                   COALESCE(
                       NULLIF(h.new_values->>'resolution', ''),
                       NULLIF(h.change_description, '')
                   ) AS resolution,
                   1 - (ce.embedding_vector <=> CAST(:query_vector AS vector)) AS similarity
            FROM complaint_embeddings AS ce
            JOIN complaints AS c ON c.complaint_id = ce.complaint_id
            LEFT JOIN departments AS d ON d.department_id = c.department_id
            LEFT JOIN categories AS cat ON cat.category_id = c.category_id
            LEFT JOIN LATERAL (
                SELECT new_values, change_description
                FROM complaint_history
                WHERE complaint_id = c.complaint_id
                  AND change_type = 'DATASET_IMPORT'
                ORDER BY history_id DESC
                LIMIT 1
            ) AS h ON TRUE
            WHERE c.status = 'RESOLVED'
              AND COALESCE(c.is_duplicate, FALSE) = FALSE
              AND UPPER(d.department_name) = UPPER(:department)
            ORDER BY ce.embedding_vector <=> CAST(:query_vector AS vector)
            LIMIT 5
            """
        ),
        {"query_vector": query_vector, "department": result["department"]},
    ).mappings().all()
    if historical:
        result["similar_complaints"] = [
            {
                "complaint_id": row["complaint_id"],
                "complaint_text": f"{row['title']} {row['description']}".strip(),
                "department": row["department"],
                "category": row["category"],
                "priority": row["priority"],
                "resolution": row["resolution"],
                "similarity": round(float(row["similarity"]), 4),
            }
            for row in historical
        ]

    chunks = db.session.execute(
        text(
            """
            SELECT k.chunk_id, k.title, k.chunk_text, k.metadata,
                   1 - (k.chunk_embedding <=> CAST(:query_vector AS vector)) AS similarity
            FROM knowledge_document_chunks AS k
            JOIN departments AS d ON d.department_id = k.department_id
            WHERE k.is_active = TRUE
              AND k.chunk_embedding IS NOT NULL
              AND UPPER(d.department_name) = UPPER(:department)
            ORDER BY k.chunk_embedding <=> CAST(:query_vector AS vector)
            LIMIT 3
            """
        ),
        {"query_vector": query_vector, "department": result["department"]},
    ).mappings().all()
    if chunks:
        result["knowledge_documents"] = [
            {
                "source": (row["metadata"] or {}).get("source", row["title"]),
                "title": row["title"],
                "text": row["chunk_text"],
                "similarity": round(float(row["similarity"]), 4),
            }
            for row in chunks
        ]
        first_guidance = next((line.strip() for line in chunks[0]["chunk_text"].splitlines() if line.strip()), "")
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
    db.session.commit()


def _user_for_identity():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        abort(401, description="Your session is invalid.")
    user = db.session.get(User, user_id)
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


def _internal_error_response(error):
    return jsonify({"error": "Internal server error."}), 500


def _public_url(value):
    value = value.strip().rstrip("/")
    return value if "://" in value else f"https://{value}"


def _sqlalchemy_database_url(value):
    database_url = make_url(value)
    if database_url.drivername == "postgresql":
        database_url = database_url.set(drivername="postgresql+psycopg2")
    return database_url.render_as_string(hide_password=False)


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
        SQLALCHEMY_DATABASE_URI=_sqlalchemy_database_url(
            os.getenv(
                "DATABASE_URL",
                "sqlite:///" + str(Path(app.instance_path) / "complaints.db").replace("\\", "/"),
            )
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
        GOOGLE_REDIRECT_URI=os.getenv("GOOGLE_REDIRECT_URI", "").strip(),
        ENABLE_GEMINI=os.getenv("ENABLE_GEMINI", "false").lower() == "true",
        FRONTEND_URL=_public_url(
            os.getenv("FRONTEND_URL")
            or os.getenv("RENDER_EXTERNAL_URL")
            or "http://localhost:5173"
        ),
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
    cors_origins = [
        _public_url(origin)
        for origin in os.getenv("CORS_ORIGINS", app.config["FRONTEND_URL"]).split(",")
        if origin.strip()
    ]
    CORS(
        app,
        supports_credentials=True,
        origins=cors_origins,
        allow_headers=["Content-Type", "X-CSRF-TOKEN"],
    )
    app.register_error_handler(400, _error_response)
    app.register_error_handler(401, _error_response)
    app.register_error_handler(403, _error_response)
    app.register_error_handler(404, _error_response)
    app.register_error_handler(409, _error_response)
    app.register_error_handler(500, _internal_error_response)
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
        if app.testing or app.config["APP_ENV"] == "test":
            db.create_all()
            _seed_reference_data()
        else:
            if db.engine.dialect.name != "postgresql":
                raise RuntimeError(
                    "Run the application with the initialized PostgreSQL database. "
                    "The finalized database schema is not generated by the ORM."
                )
            _validate_postgres_schema()

    @app.get("/api/v1/health")
    def health():
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "service": "smart-complaint-routing"})

    @app.get("/api/v1/auth/options")
    def auth_options():
        return jsonify({
            "google_enabled": oauth is not None,
            "external_ai_enabled": app.config["ENABLE_GEMINI"],
        })

    @app.post("/api/v1/auth/register")
    def register():
        abort(403, description="User and department accounts must use Google sign-in.")

    @app.post("/api/v1/auth/login")
    def login():
        body = _json_object()
        email = str(body.get("email", "")).strip().lower()
        password = body.get("password", "")
        portal = body.get("portal")
        if portal is not None and portal != "admin":
            abort(403, description="User and department accounts must use Google sign-in.")
        user = User.query.filter_by(email=email).first()
        if user is None or not user.is_active or not user.password_hash or not check_password_hash(user.password_hash, password if isinstance(password, str) else ""):
            abort(401, description="Email or password is incorrect.")
        if user.role is None or user.role.name != "ADMIN":
            abort(403, description="User and department accounts must use Google sign-in.")
        response = jsonify({"user": user.to_dict()})
        set_access_cookies(response, create_access_token(identity=str(user.id)))
        return response

    @app.get("/api/v1/auth/me")
    @jwt_required()
    def me():
        return jsonify({"user": _user_for_identity().to_dict()})

    @app.post("/api/v1/auth/logout")
    def logout():
        response = jsonify({"message": "Signed out."})
        unset_jwt_cookies(response)
        return response

    @app.get("/api/v1/auth/google")
    def google_login():
        if oauth is None:
            abort(503, description="Google sign-in is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
        portal = request.args.get("portal")
        if portal is not None:
            if portal not in {"student", "admin", "department"}:
                abort(400, description="Choose a valid portal.")
            department = request.args.get("department", "").upper()
            if portal == "department" and department not in DEPARTMENT_INFO:
                abort(400, description="Choose a valid department.")
            session["portal_intent"] = {
                "portal": portal,
                "department": department,
                "registration": request.args.get("mode") == "register",
            }
        else:
            session.pop("portal_intent", None)
        callback = app.config["GOOGLE_REDIRECT_URI"] or url_for("google_callback", _external=True)
        return oauth.google.authorize_redirect(callback)


    @app.get("/api/v1/auth/google/callback")
    def google_callback():
        if oauth is None:
            abort(503, description="Google sign-in is not configured.")

        portal_intent = session.pop("portal_intent", None)
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
        if not portal_intent or portal_intent["portal"] != "admin":
            if not _is_vit_email(email):
                abort(403, description="Use a verified VIT Google account with an .ac.in email address.")

        # Find an account already linked to this Google identity.
        user = User.query.filter_by(google_subject=subject).first()

        # If not linked, check whether this email already has an account.
        if user is None:
            user = User.query.filter_by(email=email).first()

        # Create a new account when this Google email is not registered.
        if user is None:
            if portal_intent and portal_intent["portal"] == "admin":
                abort(403, description="Administrator sign-in uses email and password.")
            if portal_intent and portal_intent["portal"] == "department" and not portal_intent["registration"]:
                abort(403, description="Submit a department access request before signing in.")
            user_role = Role.query.filter_by(name="USER").one()
            department_signup = bool(portal_intent and portal_intent["portal"] == "department")

            user = User(
                email=email,
                full_name=str(profile.get("name") or email.split("@")[0])[:120],
                user_type="WORKING_STAFF" if department_signup else "STUDENT",
                role=user_role,
                google_subject=subject,
                is_active=True,
            )
            db.session.add(user)
            if department_signup:
                user.department = portal_intent["department"]
            db.session.flush()

            _record_audit(
                user,
                "DEPARTMENT_ACCESS_REQUESTED" if department_signup else "GOOGLE_SIGN_IN",
                "user",
                user.id,
                {"department": user.department} if department_signup else None,
            )

        else:
            # Do not allow a disabled existing account to sign in.
            if not user.is_active:
                db.session.rollback()
                abort(403, description="This account is disabled.")

            if portal_intent:
                expected_roles = {"student": "USER", "admin": "ADMIN", "department": "OFFICER"}
                if user.role is None or user.role.name != expected_roles[portal_intent["portal"]]:
                    is_pending_department_request = (
                        portal_intent["portal"] == "department"
                        and portal_intent["registration"]
                        and user.user_type == "WORKING_STAFF"
                        and user.role is not None
                        and user.role.name == "USER"
                        and user.department == portal_intent["department"]
                    )
                    if not is_pending_department_request:
                        abort(403, description="This account does not have access to the selected portal.")
                if (
                    portal_intent["portal"] == "department"
                    and user.role.name == "OFFICER"
                    and user.department != portal_intent["department"]
                ):
                    abort(403, description="This account is not assigned to the selected department.")
                if (
                    portal_intent["portal"] == "department"
                    and user.role.name == "USER"
                    and not portal_intent["registration"]
                ):
                    abort(403, description="Your department access request is still awaiting administrator approval.")

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

        department_request_pending = bool(
            portal_intent
            and portal_intent["portal"] == "department"
            and user.role
            and user.role.name == "USER"
            and user.user_type == "WORKING_STAFF"
        )
        response = redirect(
            f"{app.config['FRONTEND_URL']}/?department_request=pending"
            if department_request_pending
            else app.config["FRONTEND_URL"]
        )
        if not department_request_pending:
            set_access_cookies(response, create_access_token(identity=str(user.id)))
        return response

    @app.post("/api/v1/ai/analyze")
    @_permission_required("complaint.create")
    def analyze():
        body = _json_object()
        text = str(body.get("description", "")).strip()
        if len(text) < 15 or len(text) > 5000:
            abort(400, description="Describe the issue in 15 to 5,000 characters.")
        requested_department = str(body.get("department", "")).upper()
        if requested_department not in DEPARTMENT_INFO:
            abort(400, description="Choose one of the five supported departments.")
        result = analyze_complaint(text, requested_department)
        result["department"] = requested_department
        embedding = generate_embedding(text)
        _apply_database_ai_context(result, embedding)
        result["external_ai_available"] = app.config["ENABLE_GEMINI"]
        db.session.commit()
        result.pop("embedding", None)
        return jsonify(result)

    @app.get("/api/v1/departments")
    @_permission_required("complaint.read")
    def departments():
        items = Department.query.order_by(Department.name).all()
        return jsonify({"departments": [{"name": item.name, "description": item.description} for item in items]})

    @app.get("/api/v1/complaints")
    @_permission_required("complaint.read")
    def list_complaints():
        query = Complaint.query
        if g.user.role.name == "USER":
            query = query.filter_by(reporter_id=g.user.id)
        elif g.user.role.name == "OFFICER":
            if not g.user.department:
                return jsonify({"complaints": []})
            query = query.join(
                Department,
                Complaint.department_id == Department.id,
            ).filter(Department.name == g.user.department)
        status = request.args.get("status")
        if status:
            status = status.upper()
            if status not in {"SUBMITTED", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "REJECTED"}:
                abort(400, description="Choose a valid complaint status.")
            query = query.filter_by(status=status)
        items = query.order_by(Complaint.created_at.desc()).limit(200).all()
        return jsonify({"complaints": [item.to_dict(include_description=False) for item in items]})

    @app.post("/api/v1/complaints")
    @_permission_required("complaint.create")
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
        if requested_department not in DEPARTMENT_INFO:
            abort(400, description="Choose one of the five supported departments.")
        ai_result = analyze_complaint(description, requested_department)
        ai_result["department"] = requested_department
        embedding = generate_embedding(f"{title} {description}")
        _apply_database_ai_context(ai_result, embedding)
        ai_result["external_ai_used"] = False
        if allow_external_ai:
            external_resolution, external_warning = generate_external_resolution(description, ai_result)
            if external_resolution:
                ai_result["suggested_resolution"] = external_resolution
                ai_result["model"] = "gemini"
                ai_result["external_ai_used"] = True
            if external_warning:
                ai_result["warning"] = external_warning
        department_record = Department.query.filter_by(name=requested_department).one_or_none()
        if department_record is None:
            abort(500, description="The configured department reference data is incomplete.")
        category = Category.query.filter_by(
            department_id=department_record.id,
            name=ai_result["category"],
        ).first()
        if category is None:
            category = Category(
                department_id=department_record.id,
                name=ai_result["category"],
                description="AI-suggested complaint category.",
            )
            db.session.add(category)
            db.session.flush()
        suggested_department = Department.query.filter_by(name=ai_result["department"]).first()
        complaint = Complaint(
            reporter_id=g.user.id,
            title=title,
            description=description,
            location=location,
            department_id=department_record.id,
            category_record=category,
            priority=ai_result["priority"],
            status="SUBMITTED",
            confidence_score=float(ai_result.get("confidence_score", 0.0)),
            ai_suggested_department_id=suggested_department.id if suggested_department else None,
            ai_suggested_priority=ai_result["priority"],
            rag_relevant_docs=[
                item["source"] for item in ai_result.get("knowledge_documents", [])
                if item.get("source")
            ],
        )
        db.session.add(complaint)
        db.session.flush()
        if embedding:
            db.session.add(ComplaintEmbedding(
                complaint_id=complaint.id,
                embedding=embedding,
                model_name="sentence-transformers/all-MiniLM-L6-v2",
            ))
        _record_history(complaint, g.user, "SUBMITTED", note="Complaint submitted.")
        db.session.add(ComplaintHistory(
            complaint_id=complaint.id,
            actor_id=g.user.id,
            action="AI_SUGGESTION",
            after_state={
                "department": ai_result["department"],
                "category": ai_result["category"],
                "priority": ai_result["priority"],
                "confidence_score": ai_result.get("confidence_score"),
            },
            note=ai_result["suggested_resolution"],
        ))
        _record_audit(g.user, "COMPLAINT_SUBMITTED", "complaint", complaint.id, {
            "reference": complaint.reference,
            "external_ai_used": ai_result["external_ai_used"],
        })
        db.session.commit()
        return jsonify({"complaint": complaint.to_dict()}), 201

    @app.get("/api/v1/complaints/<complaint_id>")
    @_permission_required("complaint.read")
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
    @_permission_required("complaint.read")
    def complaint_history(complaint_id):
        complaint = _complaint_or_404(complaint_id)
        items = ComplaintHistory.query.filter_by(complaint_id=complaint.id).order_by(
            ComplaintHistory.created_at.asc(),
            ComplaintHistory.id.asc(),
        ).all()
        return jsonify({"history": [item.to_dict() for item in items]})

    @app.patch("/api/v1/admin/complaints/<int:complaint_id>/department")
    @_permission_required("admin.access")
    def reassign_complaint_department(complaint_id):
        complaint = db.session.get(Complaint, complaint_id)
        if complaint is None:
            abort(404, description="Complaint not found.")
        body = _json_object()
        department_name = str(body.get("department", "")).strip().upper()
        if department_name not in DEPARTMENT_INFO:
            abort(400, description="Choose one of the five supported departments.")
        department = Department.query.filter_by(name=department_name).one_or_none()
        if department is None:
            abort(500, description="The configured department reference data is incomplete.")

        before = _history_state(complaint)
        _set_complaint_department(complaint, department)
        _record_history(
            complaint,
            g.user,
            "DEPARTMENT_REASSIGNED",
            before,
            f"Department changed from {before['department']} to {department_name}.",
        )
        _record_audit(
            g.user,
            "COMPLAINT_DEPARTMENT_REASSIGNED",
            "complaint",
            complaint.id,
            {"from": before["department"], "to": department_name},
            old_values=before,
        )
        db.session.commit()
        return jsonify({"complaint": complaint.to_dict()})

    @app.delete("/api/v1/admin/complaints/<int:complaint_id>")
    @_permission_required("complaint.delete")
    def delete_complaint(complaint_id):
        complaint = db.session.get(Complaint, complaint_id)
        if complaint is None:
            abort(404, description="Complaint not found.")
        details = {
            "reference": complaint.reference,
            "title": complaint.title,
            "status": complaint.status,
        }
        _record_audit(g.user, "COMPLAINT_DELETED", "complaint", complaint.id, details)
        history_ids = [
            item[0]
            for item in db.session.query(ComplaintHistory.id)
            .filter_by(complaint_id=complaint.id)
            .all()
        ]
        if history_ids:
            RollbackRecord.query.filter(
                RollbackRecord.reversed_history_id.in_(history_ids)
            ).update({"reversed_history_id": None}, synchronize_session=False)
            RollbackRecord.query.filter(
                RollbackRecord.rollback_history_id.in_(history_ids)
            ).update({"rollback_history_id": None}, synchronize_session=False)
        ComplaintHistory.query.filter_by(complaint_id=complaint.id).delete(synchronize_session=False)
        ComplaintEmbedding.query.filter_by(complaint_id=complaint.id).delete(synchronize_session=False)
        Feedback.query.filter_by(complaint_id=complaint.id).delete(synchronize_session=False)
        db.session.delete(complaint)
        db.session.commit()
        return jsonify({"message": f"{details['reference']} was deleted."})

    @app.patch("/api/v1/complaints/<complaint_id>/status")
    @_permission_required("complaint.update")
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

        allowed_transitions = {
            "SUBMITTED": {"ASSIGNED", "IN_PROGRESS", "REJECTED"},
            "ASSIGNED": {"IN_PROGRESS", "REJECTED"},
            "IN_PROGRESS": {"RESOLVED", "REJECTED"},
            "RESOLVED": set(),
            "REJECTED": set(),
        }
        if new_status not in allowed_transitions:
            abort(400, description="Choose a valid complaint status.")
        if g.user.role.name == "OFFICER" and new_status not in {"ASSIGNED", "IN_PROGRESS", "RESOLVED", "REJECTED"}:
            abort(403, description="Officers cannot perform that status change.")
        if new_status not in allowed_transitions.get(complaint.status, set()):
            abort(409, description=f"A complaint in {complaint.status.replace('_', ' ').title()} cannot move to {new_status.replace('_', ' ').title()}.")
        if new_status == "RESOLVED" and len(resolution) < 10:
            abort(400, description="Add at least 10 characters describing the resolution.")
        before = _history_state(complaint)
        requested_department = body.get("department")
        if requested_department is not None:
            requested_department = str(requested_department).strip().upper()
            if requested_department not in DEPARTMENT_INFO:
                abort(400, description="Choose one of the five supported departments.")
            if role == "OFFICER" and requested_department != g.user.department:
                abort(403, description="Officers may only route complaints to their own department.")
            department = Department.query.filter_by(name=requested_department).one_or_none()
            if department is None:
                abort(500, description="The configured department reference data is incomplete.")
            _set_complaint_department(complaint, department)
        if new_status == "ASSIGNED" and not complaint.department_id:
            abort(400, description="Choose a department before assigning the complaint.")
        complaint.status = new_status
        if new_status == "RESOLVED":
            complaint.resolved_at = datetime.now(timezone.utc)
        _record_history(
            complaint,
            g.user,
            new_status,
            before,
            (resolution or note)[:5000],
        )
        _record_audit(g.user, "COMPLAINT_STATUS_UPDATED", "complaint", complaint.id, {"status": new_status})
        db.session.commit()
        return jsonify({"complaint": complaint.to_dict()})

    @app.post("/api/v1/complaints/<complaint_id>/feedback")
    @_permission_required("feedback.create")
    def submit_feedback(complaint_id):
        complaint = _complaint_or_404(complaint_id)
        if complaint.reporter_id != g.user.id or complaint.status != "RESOLVED":
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
    @_permission_required("complaint.read")
    def dashboard():
        query = Complaint.query
        officer_scope_applied = False
        if g.user.role.name == "USER":
            query = query.filter_by(reporter_id=g.user.id)
        elif g.user.role.name == "OFFICER":
            query = query.join(
                Department,
                Complaint.department_id == Department.id,
            ).filter(
                Department.name == g.user.department
            ) if g.user.department else query.filter(Complaint.id == -1)
            officer_scope_applied = bool(g.user.department)
        total = query.count()
        status_rows = query.with_entities(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all()
        department_query = query if officer_scope_applied else query.join(
            Department,
            Complaint.department_id == Department.id,
        )
        department_rows = department_query.with_entities(
            Department.name, func.count(Complaint.id)
        ).group_by(Department.name).all()
        return jsonify({
            "total": total,
            "by_status": {status: count for status, count in status_rows},
            "by_department": {department: count for department, count in department_rows},
        })

    @app.get("/api/v1/admin/users")
    @_permission_required("user.update")
    def admin_users():
        users = User.query.filter(
            ~User.email.like("deleted+%@deleted.invalid")
        ).order_by(User.created_at.desc()).limit(500).all()
        return jsonify({"users": [user.to_dict() for user in users]})

    @app.get("/api/v1/admin/categories")
    @_permission_required("user.update")
    def admin_categories():
        items = Category.query.join(
            Department,
            Category.department_id == Department.id,
        ).order_by(Department.name, Category.name).all()
        return jsonify({"categories": [{"id": item.id, "department": item.department, "name": item.name} for item in items]})

    @app.post("/api/v1/admin/categories")
    @_permission_required("user.update")
    def create_category():
        body = _json_object()
        department = str(body.get("department", "")).upper()
        name = str(body.get("name", "")).strip()
        if department not in DEPARTMENT_INFO or len(name) < 2 or len(name) > 80:
            abort(400, description="Choose a supported department and a category name of 2 to 80 characters.")
        department_record = Department.query.filter_by(name=department).one_or_none()
        if department_record is None:
            abort(500, description="The configured department reference data is incomplete.")
        if Category.query.filter_by(department_id=department_record.id, name=name).first():
            abort(409, description="That category already exists for this department.")
        category = Category(department_id=department_record.id, name=name)
        db.session.add(category)
        db.session.flush()
        _record_audit(g.user, "CATEGORY_CREATED", "category", category.id, {"department": department, "name": name})
        db.session.commit()
        return jsonify({"category": {"id": category.id, "department": department, "name": name}}), 201

    @app.patch("/api/v1/admin/users/<user_id>/role")
    @_permission_required("user.update")
    def update_user_role(user_id):
        target = db.session.get(User, user_id)
        if target is None:
            abort(404, description="User not found.")
        body = _json_object()
        role_name = str(body.get("role", "")).upper()
        if role_name not in {"USER", "OFFICER", "ADMIN"}:
            abort(400, description="Role must be User, Officer, or Admin.")
        if target.id == g.user.id and role_name != "ADMIN":
            abort(400, description="You cannot remove your own administrator access.")
        department = str(body.get("department", "")).upper()
        if role_name == "OFFICER" and department not in DEPARTMENT_INFO:
            abort(400, description="Choose a department for this officer.")
        before_state = {
            "role": target.role.name if target.role else None,
            "department": target.department,
        }
        target.role = Role.query.filter_by(name=role_name).one()
        target.department = department if role_name == "OFFICER" else None
        _record_audit(
            g.user,
            "USER_ROLE_UPDATED",
            "user",
            target.id,
            {
                "from": before_state["role"],
                "to": role_name,
                "department": target.department,
            },
            old_values=before_state,
        )
        db.session.commit()
        return jsonify({"user": target.to_dict()})

    @app.patch("/api/v1/admin/users/<user_id>/active")
    @_permission_required("user.update")
    def toggle_user(user_id):
        target = db.session.get(User, user_id)
        if target is None:
            abort(404, description="User not found.")
        if target.id == g.user.id:
            abort(400, description="You cannot disable your own account.")
        body = _json_object()
        if not isinstance(body.get("is_active"), bool):
            abort(400, description="is_active must be true or false.")
        before_state = {"is_active": target.is_active}
        target.is_active = body["is_active"]
        _record_audit(
            g.user,
            "USER_ACTIVE_STATE_UPDATED",
            "user",
            target.id,
            {"is_active": target.is_active},
            old_values=before_state,
        )
        db.session.commit()
        return jsonify({"user": target.to_dict()})

    @app.delete("/api/v1/admin/users/<int:user_id>")
    @_permission_required("user.delete")
    def delete_user(user_id):
        target = db.session.get(User, user_id)
        if target is None or target.email == f"deleted+{user_id}@deleted.invalid":
            abort(404, description="User not found.")
        if target.id == g.user.id:
            abort(400, description="You cannot delete your own administrator account.")
        if target.role and target.role.name == "ADMIN":
            active_admins = User.query.join(
                user_roles,
                user_roles.c.user_id == User.id,
            ).join(
                Role,
                user_roles.c.role_id == Role.id,
            ).filter(
                Role.name == "ADMIN",
                User.is_active.is_(True),
                ~User.email.like("deleted+%@deleted.invalid"),
            ).count()
            if active_admins <= 1:
                abort(409, description="You cannot delete the last active administrator.")
        _record_audit(
            g.user,
            "USER_ANONYMIZED",
            "user",
            target.id,
            {"role": target.role.name if target.role else None},
        )
        target.full_name = "Deleted account"
        target.email = f"deleted+{target.id}@deleted.invalid"
        target.password_hash = None
        target.google_subject = None
        target.department = None
        target.profile_picture_url = None
        target.is_active = False
        db.session.commit()
        return jsonify({"message": "Account deleted. Linked complaint and audit history was retained."})

    @app.get("/api/v1/admin/audit")
    @_permission_required("admin.audit")
    def audit_logs():
        items = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
        latest_ids = {}
        latest_rows = db.session.query(
            AuditLog.resource_type,
            AuditLog.resource_id,
            func.max(AuditLog.id),
        ).filter(
            AuditLog.resource_type.isnot(None),
            AuditLog.resource_id.isnot(None),
            AuditLog.action.in_({"USER_ROLE_UPDATED", "USER_ACTIVE_STATE_UPDATED"}),
        ).group_by(AuditLog.resource_type, AuditLog.resource_id).all()
        for resource_type, resource_id, latest_id in latest_rows:
            latest_ids.setdefault(resource_type, {})[resource_id] = latest_id
        user_ids = {
            item.resource_id
            for item in items
            if item.resource_type == "user" and item.resource_id is not None
        }
        users_by_id = {
            user.id: user
            for user in User.query.filter(User.id.in_(user_ids)).all()
        } if user_ids else {}
        events = []
        for item in items:
            rollback_state = item.old_values
            if (
                not rollback_state
                and item.resource_type == "user"
                and item.action == "USER_ROLE_UPDATED"
                and item.details
                and item.details.get("from") in {"USER", "CITIZEN", "ADMIN"}
            ):
                rollback_state = {"role": _normalized_role(item.details["from"]), "department": None}
            target = users_by_id.get(item.resource_id)
            current_state_matches = False
            if target and item.action == "USER_ROLE_UPDATED" and item.details:
                current_state_matches = (
                    _normalized_role(item.details.get("to")) == _normalized_role(target.role.name if target.role else None)
                    and (
                        "department" not in item.details
                        or item.details.get("department") == target.department
                    )
                )
            elif target and item.action == "USER_ACTIVE_STATE_UPDATED" and item.details:
                current_state_matches = item.details.get("is_active") is target.is_active
            events.append({
                **item.to_dict(),
                "old_values": rollback_state,
                "can_rollback": (
                    item.resource_type == "user"
                    and item.action in {"USER_ROLE_UPDATED", "USER_ACTIVE_STATE_UPDATED"}
                    and rollback_state is not None
                    and current_state_matches
                    and latest_ids.get(item.resource_type, {}).get(item.resource_id) == item.id
                ),
            })
        return jsonify({"events": events})

    @app.post("/api/v1/admin/audit/<int:audit_id>/rollback")
    @_permission_required("admin.access")
    def rollback_audit_event(audit_id):
        event = db.session.get(AuditLog, audit_id)
        if event is None:
            abort(404, description="Audit event not found.")
        if event.resource_type != "user" or event.action not in {
            "USER_ROLE_UPDATED",
            "USER_ACTIVE_STATE_UPDATED",
        }:
            abort(400, description="This audit event does not contain reversible user access changes.")
        latest = AuditLog.query.filter_by(
            resource_type=event.resource_type,
            resource_id=event.resource_id,
        ).filter(
            AuditLog.action.in_({"USER_ROLE_UPDATED", "USER_ACTIVE_STATE_UPDATED"}),
        ).order_by(AuditLog.id.desc()).first()
        if latest is None or latest.id != event.id:
            abort(409, description="Only the latest user access change can be rolled back.")
        target = db.session.get(User, event.resource_id)
        if target is None or target.email == f"deleted+{event.resource_id}@deleted.invalid":
            abort(409, description="An anonymized account cannot be restored from an audit event.")

        previous_values = event.old_values
        if (
            not previous_values
            and event.action == "USER_ROLE_UPDATED"
            and event.details
            and event.details.get("from") in {"USER", "CITIZEN", "ADMIN"}
        ):
            previous_values = {"role": _normalized_role(event.details["from"]), "department": None}
        if not previous_values:
            abort(400, description="This audit event does not contain enough prior state to roll back safely.")

        if event.action == "USER_ROLE_UPDATED":
            old_role = previous_values.get("role")
            old_role = _normalized_role(old_role)
            if old_role not in {"USER", "OFFICER", "ADMIN"}:
                abort(409, description="The previous account role is unavailable.")
            old_department = previous_values.get("department")
            if old_role == "OFFICER" and old_department not in DEPARTMENT_INFO:
                abort(409, description="The previous officer department is unavailable.")
            if _normalized_role(event.details.get("to")) != _normalized_role(target.role.name if target.role else None):
                abort(409, description="The user's role has changed since this audit event.")
            if "department" in event.details and event.details.get("department") != target.department:
                abort(409, description="The user's department has changed since this audit event.")
            if target.id == g.user.id and old_role != "ADMIN":
                abort(400, description="You cannot remove your own administrator access.")
            if target.role and target.role.name == "ADMIN" and old_role != "ADMIN":
                active_admins = User.query.join(
                    user_roles,
                    user_roles.c.user_id == User.id,
                ).join(
                    Role,
                    user_roles.c.role_id == Role.id,
                ).filter(
                    Role.name == "ADMIN",
                    User.is_active.is_(True),
                    ~User.email.like("deleted+%@deleted.invalid"),
                ).count()
                if active_admins <= 1:
                    abort(409, description="Rolling back this change would remove the last active administrator.")
            current_state = {
                "role": target.role.name if target.role else None,
                "department": target.department,
            }
            target.role = Role.query.filter_by(name=old_role).one()
            target.department = old_department if old_role == "OFFICER" else None
            restored_state = {"role": old_role, "department": target.department}
        else:
            old_active = previous_values.get("is_active")
            if not isinstance(old_active, bool):
                abort(409, description="The previous account status is unavailable.")
            if event.details.get("is_active") is not target.is_active:
                abort(409, description="The user's account status has changed since this audit event.")
            current_state = {"is_active": target.is_active}
            target.is_active = old_active
            restored_state = {"is_active": old_active}

        _record_audit(
            g.user,
            "USER_ACCESS_ROLLED_BACK",
            "user",
            target.id,
            {"audit_id": event.id, "restored": restored_state},
            old_values=current_state,
        )
        db.session.commit()
        return jsonify({"user": target.to_dict(), "message": "The latest user access change was rolled back."})

    @app.post("/api/v1/admin/complaints/<complaint_id>/rollback")
    @_permission_required("admin.access")
    def rollback_complaint(complaint_id):
        complaint = db.session.get(Complaint, complaint_id)
        if complaint is None:
            abort(404, description="Complaint not found.")
        body = _json_object()
        history_id = body.get("history_id")
        if isinstance(history_id, bool) or not (
            isinstance(history_id, int) and history_id > 0
            or isinstance(history_id, str) and history_id.isdecimal()
        ):
            abort(400, description="history_id must identify a complaint history event.")
        history = db.session.get(ComplaintHistory, int(history_id))
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
        rollback_history = _record_history(
            complaint,
            g.user,
            "ADMIN_ROLLBACK",
            before_rollback,
            f"Reversed history event {history.id}.",
        )
        db.session.flush()
        _record_audit(
            g.user,
            "COMPLAINT_ROLLED_BACK",
            "complaint",
            complaint.id,
            {
                "reversed_history_id": history.id,
                "rollback_history_id": rollback_history.id,
            },
        )
        db.session.flush()
        db.session.add(RollbackRecord(
            actor_id=g.user.id,
            status="COMPLETED",
            reason=f"Reversed complaint history event {history.id}.",
            reversed_history_id=history.id,
            rollback_history_id=rollback_history.id,
            completed_at=datetime.now(timezone.utc),
        ))
        db.session.commit()
        return jsonify({
            "complaint": complaint.to_dict(),
            "reversed_activity_id": history.id,
            "rollback_activity_id": rollback_history.id,
        })

    @app.get("/api/v1/admin/backups")
    @_permission_required("backup.manage")
    def list_backups():
        items = BackupRecord.query.order_by(BackupRecord.created_at.desc()).limit(100).all()
        return jsonify({"backups": [item.to_dict() for item in items]})

    @app.post("/api/v1/admin/backups")
    @_permission_required("backup.manage")
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
        record = BackupRecord(
            actor_id=g.user.id,
            filename=filename,
            operation="FULL",
            backup_location=str(backup_path),
            status="COMPLETED",
        )
        db.session.add(record)
        db.session.flush()
        _record_audit(g.user, "DATABASE_BACKUP_CREATED", "backup", record.id, {"filename": filename})
        db.session.commit()
        return jsonify({"backup": record.to_dict()}), 201

    @app.get("/api/v1/admin/backups/<backup_id>/download")
    @_permission_required("backup.manage")
    def download_backup(backup_id):
        record = db.session.get(BackupRecord, backup_id)
        if record is None:
            abort(404, description="Backup not found.")
        path = Path(app.config["BACKUP_DIR"]) / record.filename
        if not path.is_file():
            abort(404, description="Backup file is no longer available.")
        return send_file(path, as_attachment=True, download_name=record.filename)

    @app.post("/api/v1/admin/backups/<backup_id>/restore")
    @_permission_required("backup.manage")
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
        db.session.add(BackupRecord(
            actor_id=g.user.id,
            filename=pre_restore_name,
            operation="PRE_RESTORE",
            backup_location=str(Path(app.config["BACKUP_DIR"]) / pre_restore_name),
            status="COMPLETED",
        ))
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
