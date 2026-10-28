import unittest
from unittest.mock import Mock, patch

from flask import redirect
from flask_jwt_extended import create_access_token
from sqlalchemy.engine import make_url
from werkzeug.security import generate_password_hash

from backend.app import _is_vit_email, _sqlalchemy_database_url, create_app
from backend.models import (
    AuditLog,
    Category,
    Complaint,
    ComplaintEmbedding,
    ComplaintHistory,
    Department,
    Feedback,
    Role,
    RollbackRecord,
    User,
    db,
)


class AuthenticationAuthorizationTests(unittest.TestCase):
    def test_postgresql_urls_use_the_installed_psycopg2_driver(self):
        database_url = _sqlalchemy_database_url("postgresql://user:pass@db.example/app")
        self.assertEqual(make_url(database_url).drivername, "postgresql+psycopg2")

    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "APP_ENV": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_COOKIE_CSRF_PROTECT": False,
            "JWT_COOKIE_SECURE": False,
            "SECRET_KEY": "test-secret-key-with-enough-length-123",
            "JWT_SECRET_KEY": "test-jwt-secret-with-enough-length-456",
            "FRONTEND_URL": "http://localhost:5173",
            "ENABLE_GEMINI": False,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def create_test_account(self, data):
        with self.app.app_context():
            user_type = data.get("user_type", "STUDENT")
            department = None
            if data.get("portal") == "department":
                user_type = "WORKING_STAFF"
                department = data["department"]
            user = User(
                email=data["email"].strip().lower(),
                full_name=data["full_name"],
                password_hash=generate_password_hash(
                    data.get("password", "A-strong-demo-password"),
                    method="scrypt",
                ),
                user_type=user_type,
                role=Role.query.filter_by(name="USER").one(),
            )
            db.session.add(user)
            user.department = department
            db.session.commit()
            account = {"user": user.to_dict()}
            token = create_access_token(identity=str(user.id))
        self.client.set_cookie("access_token_cookie", token, path="/api/")
        return account

    def test_health_checks_database_connectivity(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_logout_clears_cookies_even_without_an_access_token(self):
        response = self.client.post("/api/v1/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["message"], "Signed out.")
        self.assertTrue(any(
            cookie.startswith("access_token_cookie=") and "Expires=Thu, 01 Jan 1970" in cookie
            for cookie in response.headers.getlist("Set-Cookie")
        ))

    def test_password_registration_is_disabled_for_users_and_departments(self):
        invalid_email = self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        self.assertEqual(invalid_email.status_code, 403)
        invalid_vit_domain = self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@evitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        self.assertEqual(invalid_vit_domain.status_code, 403)

        response = self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
            "role": "ADMIN",
        })
        self.assertEqual(response.status_code, 403)
        self.assertIn("Google", response.json["error"])
        self.assertTrue(_is_vit_email("student@vitstudent.ac.in"))
        self.assertFalse(_is_vit_email("student@evitstudent.ac.in"))

    def test_user_cannot_access_admin_user_management(self):
        self.create_test_account({
            "full_name": "Test Student",
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        response = self.client.get("/api/v1/admin/users")
        self.assertEqual(response.status_code, 403)

    def test_login_rejects_invalid_password(self):
        self.create_test_account({
            "full_name": "Test Student",
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        self.client.post("/api/v1/auth/logout")
        response = self.client.post("/api/v1/auth/login", json={
            "email": "student@vitstudent.ac.in",
            "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 401)

    def test_password_login_is_restricted_to_admin(self):
        self.create_test_account({
            "full_name": "Test Student",
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        denied_admin = self.client.post("/api/v1/auth/login", json={
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        self.assertEqual(denied_admin.status_code, 403)
        accepted_student = self.client.post("/api/v1/auth/login", json={
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        self.assertEqual(accepted_student.status_code, 403)
        student_without_portal = self.client.post("/api/v1/auth/login", json={
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
        })
        self.assertEqual(student_without_portal.status_code, 403)

        self.create_test_account({
            "full_name": "Test Officer",
            "email": "officer@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            officer = User.query.filter_by(email="officer@vitstudent.ac.in").one()
            officer.role = Role.query.filter_by(name="OFFICER").one()
            officer.department = "PLUMBING"
            db.session.commit()

        denied_department = self.client.post("/api/v1/auth/login", json={
            "email": "officer@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "FINANCE",
        })
        self.assertEqual(denied_department.status_code, 403)
        accepted_department = self.client.post("/api/v1/auth/login", json={
            "email": "officer@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "PLUMBING",
        })
        self.assertEqual(accepted_department.status_code, 403)

        self.create_test_account({
            "full_name": "Test Admin",
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@vitstudent.ac.in").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            db.session.commit()
        admin_login = self.client.post("/api/v1/auth/login", json={
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        self.assertEqual(admin_login.status_code, 200)

    def test_department_password_signup_and_password_login_are_rejected(self):
        response = self.client.post("/api/v1/auth/register", json={
            "full_name": "Department Applicant",
            "email": "applicant@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "PLUMBING",
        })
        self.assertEqual(response.status_code, 403)
        applicant = self.create_test_account({
            "full_name": "Department Applicant",
            "email": "applicant@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "PLUMBING",
        })
        self.assertEqual(applicant["user"]["role"], "USER")
        self.assertEqual(applicant["user"]["user_type"], "WORKING_STAFF")
        self.assertEqual(applicant["user"]["department"], "PLUMBING")
        self.client.post("/api/v1/auth/logout")
        login = self.client.post("/api/v1/auth/login", json={
            "email": "applicant@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "PLUMBING",
        })
        self.assertEqual(login.status_code, 403)
        target_id = applicant["user"]["id"]
        self.create_test_account({
            "full_name": "Test Admin",
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@vitstudent.ac.in").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            db.session.commit()
        approved = self.client.patch(
            f"/api/v1/admin/users/{target_id}/role",
            json={"role": "OFFICER", "department": "PLUMBING"},
        )
        self.assertEqual(approved.status_code, 200)
        self.client.post("/api/v1/auth/logout")
        approved_login = self.client.post("/api/v1/auth/login", json={
            "email": "applicant@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "PLUMBING",
        })
        self.assertEqual(approved_login.status_code, 403)

    def test_google_sign_in_uses_configured_callback_and_department_intent(self):
        oauth = Mock()
        oauth.google.authorize_redirect.return_value = redirect("https://accounts.google.com/")
        oauth.google.authorize_access_token.return_value = {"userinfo": {
            "email": "officer@vitstudent.ac.in",
            "email_verified": True,
            "sub": "google-officer",
            "name": "Test Officer",
        }}
        with patch("backend.app.OAuth", return_value=oauth):
            app = create_app({
                "TESTING": True,
                "APP_ENV": "test",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "JWT_COOKIE_CSRF_PROTECT": False,
                "GOOGLE_CLIENT_ID": "test-client",
                "GOOGLE_CLIENT_SECRET": "test-secret",
                "GOOGLE_REDIRECT_URI": "http://localhost:5000/api/v1/auth/google/callback",
                "FRONTEND_URL": "http://localhost:3000",
            })

        client = app.test_client()
        with app.app_context():
            officer = User(
                email="officer@vitstudent.ac.in",
                full_name="Test Officer",
                password_hash=generate_password_hash("A-strong-demo-password", method="scrypt"),
                user_type="WORKING_STAFF",
                role=Role.query.filter_by(name="USER").one(),
            )
            db.session.add(officer)
            db.session.flush()
            officer.role = Role.query.filter_by(name="OFFICER").one()
            officer.department = "PLUMBING"
            db.session.commit()

        try:
            start = client.get("/api/v1/auth/google?portal=department&department=FINANCE")
            self.assertEqual(start.status_code, 302)
            oauth.google.authorize_redirect.assert_called_with(
                "http://localhost:5000/api/v1/auth/google/callback"
            )
            denied = client.get("/api/v1/auth/google/callback")
            self.assertEqual(denied.status_code, 403)

            client.get("/api/v1/auth/google?portal=department&department=PLUMBING")
            accepted = client.get("/api/v1/auth/google/callback")
            self.assertEqual(accepted.status_code, 302)
            self.assertEqual(accepted.headers["Location"], "http://localhost:3000")
        finally:
            with app.app_context():
                db.session.remove()
                db.drop_all()

    def test_google_department_registration_creates_a_pending_access_request(self):
        oauth = Mock()
        oauth.google.authorize_redirect.return_value = redirect("https://accounts.google.com/")
        oauth.google.authorize_access_token.return_value = {"userinfo": {
            "email": "new-officer@vitstudent.ac.in",
            "email_verified": True,
            "sub": "google-new-officer",
            "name": "New Officer",
        }}
        with patch("backend.app.OAuth", return_value=oauth):
            app = create_app({
                "TESTING": True,
                "APP_ENV": "test",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "JWT_COOKIE_CSRF_PROTECT": False,
                "GOOGLE_CLIENT_ID": "test-client",
                "GOOGLE_CLIENT_SECRET": "test-secret",
                "FRONTEND_URL": "http://localhost:3000",
            })

        client = app.test_client()
        try:
            admin_sso = client.get("/api/v1/auth/google?portal=admin")
            self.assertIn(admin_sso.status_code, {302, 303})
            client.get("/api/v1/auth/google?portal=department&department=FINANCE&mode=register")
            response = client.get("/api/v1/auth/google/callback")
            self.assertEqual(response.status_code, 302)
            self.assertEqual(
                response.headers["Location"],
                "http://localhost:3000/?department_request=pending",
            )
            self.assertFalse(any(
                cookie.startswith("access_token_cookie=")
                for cookie in response.headers.getlist("Set-Cookie")
            ))
            with app.app_context():
                applicant = User.query.filter_by(email="new-officer@vitstudent.ac.in").one()
                self.assertEqual(applicant.user_type, "WORKING_STAFF")
                self.assertEqual(applicant.role.name, "USER")
                self.assertEqual(applicant.department, "FINANCE")
        finally:
            with app.app_context():
                db.session.remove()
                db.drop_all()

    def test_officer_can_access_the_department_queue(self):
        self.create_test_account({
            "full_name": "Test Student",
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        with self.app.app_context():
            student = User.query.filter_by(email="student@vitstudent.ac.in").one()
            plumbing = Department.query.filter_by(name="PLUMBING").one()
            student_complaint = Complaint(
                reporter_id=student.id,
                title="Student plumbing report",
                description="A student reports a plumbing problem in the residence.",
                department_id=plumbing.id,
                priority="MEDIUM",
                status="SUBMITTED",
                submission_mode="WEB",
            )
            db.session.add(student_complaint)
            db.session.commit()
        self.client.post("/api/v1/auth/logout")

        self.create_test_account({
            "full_name": "Test Admin",
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@vitstudent.ac.in").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            plumbing = Department.query.filter_by(name="PLUMBING").one()
            admin_complaint = Complaint(
                reporter_id=admin.id,
                title="Admin plumbing report",
                description="An administrator reports a plumbing problem on campus.",
                department_id=plumbing.id,
                priority="HIGH",
                status="SUBMITTED",
                submission_mode="WEB",
            )
            db.session.add(admin_complaint)
            db.session.commit()
        self.client.post("/api/v1/auth/logout")

        self.create_test_account({
            "full_name": "Test Officer",
            "email": "officer@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            officer = User.query.filter_by(email="officer@vitstudent.ac.in").one()
            officer.role = Role.query.filter_by(name="OFFICER").one()
            officer.department = "PLUMBING"
            db.session.commit()
        response = self.client.get("/api/v1/complaints")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["complaints"]), 2)
        self.assertEqual(self.client.get("/api/v1/dashboard").status_code, 200)

        self.client.post("/api/v1/auth/logout")
        admin_login = self.client.post("/api/v1/auth/login", json={
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        self.assertEqual(admin_login.status_code, 200)
        admin_complaints = self.client.get("/api/v1/complaints")
        self.assertEqual(admin_complaints.status_code, 200)
        self.assertEqual(len(admin_complaints.json["complaints"]), 2)

    def test_admin_can_anonymize_account_without_removing_complaint_history(self):
        self.create_test_account({
            "full_name": "Test Admin",
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        self.client.post("/api/v1/auth/logout")
        self.create_test_account({
            "full_name": "Account to Delete",
            "email": "delete-me@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@vitstudent.ac.in").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            target = User.query.filter_by(email="delete-me@vitstudent.ac.in").one()
            plumbing = Department.query.filter_by(name="PLUMBING").one()
            complaint = Complaint(
                reporter_id=target.id,
                title="Retained complaint",
                description="This complaint remains after account anonymization.",
                department_id=plumbing.id,
                priority="MEDIUM",
                status="SUBMITTED",
                submission_mode="WEB",
            )
            db.session.add(complaint)
            db.session.commit()
            target_id = target.id
            complaint_id = complaint.id

        self.client.post("/api/v1/auth/logout")
        login = self.client.post("/api/v1/auth/login", json={
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        self.assertEqual(login.status_code, 200)
        deleted = self.client.delete(f"/api/v1/admin/users/{target_id}")
        self.assertEqual(deleted.status_code, 200, deleted.json)
        self.assertIn("history was retained", deleted.json["message"])
        user_list = self.client.get("/api/v1/admin/users")
        self.assertNotIn(target_id, [user["id"] for user in user_list.json["users"]])
        with self.app.app_context():
            target = db.session.get(User, target_id)
            complaint = db.session.get(Complaint, complaint_id)
            self.assertEqual(target.email, f"deleted+{target_id}@deleted.invalid")
            self.assertEqual(target.full_name, "Deleted account")
            self.assertFalse(target.is_active)
            self.assertEqual(complaint.reporter_id, target_id)

    def test_admin_can_rollback_latest_role_change_from_audit_or_people_access(self):
        self.create_test_account({
            "full_name": "Test Admin",
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        self.client.post("/api/v1/auth/logout")
        registered = self.create_test_account({
            "full_name": "Test Student",
            "email": "student@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        target_id = registered["user"]["id"]
        self.client.post("/api/v1/auth/logout")
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@vitstudent.ac.in").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            db.session.commit()

        self.client.post("/api/v1/auth/login", json={
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        changed = self.client.patch(
            f"/api/v1/admin/users/{target_id}/role",
            json={"role": "OFFICER", "department": "PLUMBING"},
        )
        self.assertEqual(changed.status_code, 200, changed.json)
        events = self.client.get("/api/v1/admin/audit").json["events"]
        role_event = next(event for event in events if event["action"] == "USER_ROLE_UPDATED")
        self.assertTrue(role_event["can_rollback"])
        self.assertEqual(role_event["old_values"]["role"], "USER")
        with self.app.app_context():
            legacy_event = db.session.get(AuditLog, role_event["id"])
            legacy_event.old_values = None
            legacy_event.details = {**legacy_event.details, "from": "CITIZEN"}
            db.session.commit()
        events = self.client.get("/api/v1/admin/audit").json["events"]
        role_event = next(event for event in events if event["id"] == role_event["id"])
        self.assertTrue(role_event["can_rollback"])

        rolled_back = self.client.post(
            f"/api/v1/admin/audit/{role_event['id']}/rollback",
            json={},
        )
        self.assertEqual(rolled_back.status_code, 200)
        self.assertEqual(rolled_back.json["user"]["role"], "USER")
        self.assertIsNone(rolled_back.json["user"]["department"])
        events = self.client.get("/api/v1/admin/audit").json["events"]
        self.assertFalse(next(event for event in events if event["id"] == role_event["id"])["can_rollback"])
        self.assertEqual(
            self.client.post(f"/api/v1/admin/audit/{role_event['id']}/rollback", json={}).status_code,
            409,
        )

    def test_complaint_creation_and_status_workflow_follow_database_states(self):
        self.create_test_account({
            "full_name": "Test Citizen",
            "email": "citizen@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        ai_result = {
            "department": "PLUMBING",
            "category": "Water Leakage",
            "priority": "HIGH",
            "confidence_score": 0.9,
            "suggested_resolution": "Have the plumbing team inspect the pipe.",
            "knowledge_documents": [],
            "similar_complaints": [],
            "duplicate": False,
            "model": "test",
        }
        with patch("backend.app.analyze_complaint", return_value=ai_result), patch(
            "backend.app.generate_embedding", return_value=None
        ):
            response = self.client.post("/api/v1/complaints", json={
                "title": "Pipe leaking in the dorm",
                "description": "A water pipe is leaking near the dormitory entrance.",
                "location": "Dorm entrance",
                "department": "PLUMBING",
            })
        self.assertEqual(response.status_code, 201)
        complaint_id = response.json["complaint"]["id"]
        history_response = self.client.get(
            f"/api/v1/complaints/{complaint_id}/history"
        )
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(
            [item["action"] for item in history_response.json["history"]],
            ["SUBMITTED", "AI_SUGGESTION"],
        )
        self.client.post("/api/v1/auth/logout")

        self.create_test_account({
            "full_name": "Test Officer",
            "email": "assigned-officer@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            officer = User.query.filter_by(email="assigned-officer@vitstudent.ac.in").one()
            officer.role = Role.query.filter_by(name="OFFICER").one()
            officer.department = "PLUMBING"
            db.session.commit()

        assigned = self.client.patch(
            f"/api/v1/complaints/{complaint_id}/status",
            json={"status": "ASSIGNED", "department": "PLUMBING"},
        )
        self.assertEqual(assigned.status_code, 200)
        progressing = self.client.patch(
            f"/api/v1/complaints/{complaint_id}/status",
            json={"status": "IN_PROGRESS", "department": "PLUMBING"},
        )
        self.assertEqual(progressing.status_code, 200)
        missing_resolution = self.client.patch(
            f"/api/v1/complaints/{complaint_id}/status",
            json={"status": "RESOLVED", "department": "PLUMBING"},
        )
        self.assertEqual(missing_resolution.status_code, 400)
        resolved = self.client.patch(
            f"/api/v1/complaints/{complaint_id}/status",
            json={
                "status": "RESOLVED",
                "department": "PLUMBING",
                "resolution": "The leaking pipe was repaired and tested.",
            },
        )
        self.assertEqual(resolved.status_code, 200)

        rejected_transition = self.client.patch(
            f"/api/v1/complaints/{complaint_id}/status",
            json={"status": "ASSIGNED", "department": "PLUMBING"},
        )
        self.assertEqual(rejected_transition.status_code, 409)
        with self.app.app_context():
            complaint = db.session.get(Complaint, complaint_id)
            self.assertEqual(complaint.status, "RESOLVED")
            resolution_event = ComplaintHistory.query.filter_by(
                complaint_id=complaint_id,
                action="RESOLVED",
            ).one()
            self.assertEqual(
                resolution_event.note,
                "The leaking pipe was repaired and tested.",
            )

    def test_analysis_requires_the_user_selected_department(self):
        self.create_test_account({
            "full_name": "Test User",
            "email": "user@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        response = self.client.post("/api/v1/ai/analyze", json={
            "description": "There is a water leak in the residence hall.",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("department", response.json["error"].lower())

    def test_complaint_department_uses_the_users_selection_not_the_ai_prediction(self):
        self.create_test_account({
            "full_name": "Test User",
            "email": "user@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        ai_result = {
            "department": "PLUMBING",
            "category": "Water Leakage",
            "priority": "HIGH",
            "confidence_score": 0.9,
            "suggested_resolution": "Ask the selected team to inspect the concern.",
            "knowledge_documents": [],
            "similar_complaints": [],
            "duplicate": False,
            "model": "test",
        }
        with patch("backend.app.analyze_complaint", return_value=ai_result), patch(
            "backend.app.generate_embedding",
            return_value=None,
        ):
            response = self.client.post("/api/v1/complaints", json={
                "title": "Water concern in a different team",
                "description": "There is a water concern that I want the security team to review.",
                "department": "SECURITY",
            })
        self.assertEqual(response.status_code, 201)
        complaint = response.json["complaint"]
        self.assertEqual(complaint["department"], "SECURITY")
        self.assertEqual(complaint["ai"]["department"], "SECURITY")
        self.assertEqual(complaint["priority"], "HIGH")

    def test_admin_can_reassign_resolved_complaint_and_record_history(self):
        self.create_test_account({
            "full_name": "Test Admin",
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@vitstudent.ac.in").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            plumbing = Department.query.filter_by(name="PLUMBING").one()
            category = Category(
                department_id=plumbing.id,
                name="Test plumbing category",
            )
            db.session.add(category)
            db.session.flush()
            complaint = Complaint(
                reporter_id=admin.id,
                title="Resolved plumbing concern",
                description="A resolved plumbing concern for department reassignment.",
                department_record=plumbing,
                category_record=category,
                priority="MEDIUM",
                status="RESOLVED",
                submission_mode="WEB",
            )
            db.session.add(complaint)
            db.session.commit()
            complaint_id = complaint.id

        response = self.client.patch(
            f"/api/v1/admin/complaints/{complaint_id}/department",
            json={"department": "SECURITY"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["complaint"]["department"], "SECURITY")
        with self.app.app_context():
            complaint = db.session.get(Complaint, complaint_id)
            history = ComplaintHistory.query.filter_by(
                complaint_id=complaint_id,
                action="DEPARTMENT_REASSIGNED",
            ).one()
            audit = AuditLog.query.filter_by(
                action="COMPLAINT_DEPARTMENT_REASSIGNED",
                resource_id=complaint_id,
            ).one()
            self.assertEqual(complaint.status, "RESOLVED")
            self.assertEqual(history.before_state["department"], "PLUMBING")
            self.assertEqual(history.after_state["department"], "SECURITY")
            self.assertEqual(audit.details, {"from": "PLUMBING", "to": "SECURITY"})

    def test_admin_can_delete_complaint_and_related_records(self):
        self.create_test_account({
            "full_name": "Test Admin",
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@vitstudent.ac.in").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            complaint = Complaint(
                reporter_id=admin.id,
                title="Complaint to delete",
                description="This complaint and its dependent data are removed.",
                priority="LOW",
                status="SUBMITTED",
                submission_mode="WEB",
            )
            db.session.add(complaint)
            db.session.flush()
            complaint_id = complaint.id
            history = ComplaintHistory(
                complaint_id=complaint_id,
                actor_id=admin.id,
                action="SUBMITTED",
                after_state={"status": "SUBMITTED"},
            )
            db.session.add(history)
            db.session.flush()
            db.session.add(RollbackRecord(
                status="COMPLETED",
                reversed_history_id=history.id,
                rollback_history_id=history.id,
            ))
            db.session.add(ComplaintEmbedding(
                complaint_id=complaint_id,
                embedding=[0.0] * 384,
            ))
            db.session.add(Feedback(
                complaint_id=complaint_id,
                user_id=admin.id,
                rating=5,
            ))
            db.session.commit()

        response = self.client.delete(f"/api/v1/admin/complaints/{complaint_id}")
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertIsNone(db.session.get(Complaint, complaint_id))
            self.assertEqual(ComplaintHistory.query.filter_by(complaint_id=complaint_id).count(), 0)
            self.assertEqual(ComplaintEmbedding.query.filter_by(complaint_id=complaint_id).count(), 0)
            self.assertEqual(Feedback.query.filter_by(complaint_id=complaint_id).count(), 0)
            rollback_record = RollbackRecord.query.one()
            self.assertIsNone(rollback_record.reversed_history_id)
            self.assertIsNone(rollback_record.rollback_history_id)
            self.assertEqual(
                AuditLog.query.filter_by(
                    action="COMPLAINT_DELETED",
                    resource_id=complaint_id,
                ).count(),
                1,
            )

    def test_complaint_rollback_records_before_and_after_activity_ids(self):
        self.create_test_account({
            "full_name": "Test Admin",
            "email": "admin@vitstudent.ac.in",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@vitstudent.ac.in").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            plumbing = Department.query.filter_by(name="PLUMBING").one()
            complaint = Complaint(
                reporter_id=admin.id,
                title="Rollback activity test",
                description="A complaint used to validate reversible activity IDs.",
                department_record=plumbing,
                priority="HIGH",
                status="IN_PROGRESS",
                submission_mode="WEB",
            )
            db.session.add(complaint)
            db.session.flush()
            activity = ComplaintHistory(
                complaint_id=complaint.id,
                actor_id=admin.id,
                action="IN_PROGRESS",
                before_state={
                    "status": "ASSIGNED",
                    "department": "PLUMBING",
                    "category_id": None,
                    "priority": "MEDIUM",
                },
                after_state={
                    "status": "IN_PROGRESS",
                    "department": "PLUMBING",
                    "category_id": None,
                    "priority": "HIGH",
                },
            )
            db.session.add(activity)
            db.session.commit()
            complaint_id = complaint.id
            activity_id = activity.id

        response = self.client.post(
            f"/api/v1/admin/complaints/{complaint_id}/rollback",
            json={"history_id": activity_id},
        )
        self.assertEqual(response.status_code, 200)
        rollback_activity_id = response.json["rollback_activity_id"]
        self.assertEqual(response.json["reversed_activity_id"], activity_id)
        with self.app.app_context():
            record = RollbackRecord.query.one()
            self.assertEqual(record.reversed_history_id, activity_id)
            self.assertEqual(record.rollback_history_id, rollback_activity_id)
            rollback_audit = AuditLog.query.filter_by(
                action="COMPLAINT_ROLLED_BACK",
                resource_id=complaint_id,
            ).one()
            self.assertEqual(rollback_audit.details["reversed_history_id"], activity_id)
            self.assertEqual(rollback_audit.details["rollback_history_id"], rollback_activity_id)


if __name__ == "__main__":
    unittest.main()
