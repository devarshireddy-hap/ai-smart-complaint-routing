import unittest
from unittest.mock import Mock, patch

from flask import redirect
from backend.app import create_app
from backend.models import AuditLog, Complaint, ComplaintHistory, Department, Role, User, db


class AuthenticationAuthorizationTests(unittest.TestCase):
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

    def test_health_checks_database_connectivity(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")

    def test_registration_always_creates_citizen(self):
        response = self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
            "role": "ADMIN",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["user"]["role"], "CITIZEN")
        self.assertNotIn("password_hash", response.json["user"])

    def test_citizen_cannot_access_admin_user_management(self):
        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        response = self.client.get("/api/v1/admin/users")
        self.assertEqual(response.status_code, 403)

    def test_login_rejects_invalid_password(self):
        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        self.client.post("/api/v1/auth/logout")
        response = self.client.post("/api/v1/auth/login", json={
            "email": "student@example.edu",
            "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 401)

    def test_portal_login_checks_role_and_assigned_department(self):
        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        denied_admin = self.client.post("/api/v1/auth/login", json={
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        self.assertEqual(denied_admin.status_code, 403)
        accepted_student = self.client.post("/api/v1/auth/login", json={
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "portal": "student",
        })
        self.assertEqual(accepted_student.status_code, 200)

        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Officer",
            "email": "officer@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            officer = User.query.filter_by(email="officer@example.edu").one()
            officer.role = Role.query.filter_by(name="OFFICER").one()
            officer.department = "PLUMBING"
            db.session.commit()

        denied_department = self.client.post("/api/v1/auth/login", json={
            "email": "officer@example.edu",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "FINANCE",
        })
        self.assertEqual(denied_department.status_code, 403)
        accepted_department = self.client.post("/api/v1/auth/login", json={
            "email": "officer@example.edu",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "PLUMBING",
        })
        self.assertEqual(accepted_department.status_code, 200)

    def test_department_registration_creates_pending_non_officer_account(self):
        response = self.client.post("/api/v1/auth/register", json={
            "full_name": "Department Applicant",
            "email": "applicant@example.edu",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "PLUMBING",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["user"]["role"], "CITIZEN")
        self.assertEqual(response.json["user"]["user_type"], "WORKING_STAFF")
        self.assertEqual(response.json["user"]["department"], "PLUMBING")
        self.client.post("/api/v1/auth/logout")
        login = self.client.post("/api/v1/auth/login", json={
            "email": "applicant@example.edu",
            "password": "A-strong-demo-password",
            "portal": "department",
            "department": "PLUMBING",
        })
        self.assertEqual(login.status_code, 403)

    def test_google_sign_in_uses_configured_callback_and_department_intent(self):
        oauth = Mock()
        oauth.google.authorize_redirect.return_value = redirect("https://accounts.google.com/")
        oauth.google.authorize_access_token.return_value = {"userinfo": {
            "email": "officer@example.edu",
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
        client.post("/api/v1/auth/register", json={
            "full_name": "Test Officer",
            "email": "officer@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with app.app_context():
            officer = User.query.filter_by(email="officer@example.edu").one()
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

    def test_officer_can_access_the_department_queue(self):
        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        with self.app.app_context():
            student = User.query.filter_by(email="student@example.edu").one()
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

        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Admin",
            "email": "admin@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@example.edu").one()
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

        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Officer",
            "email": "officer@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            officer = User.query.filter_by(email="officer@example.edu").one()
            officer.role = Role.query.filter_by(name="OFFICER").one()
            officer.department = "PLUMBING"
            db.session.commit()
        response = self.client.get("/api/v1/complaints")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["complaints"]), 2)
        self.assertEqual(self.client.get("/api/v1/dashboard").status_code, 200)

        self.client.post("/api/v1/auth/logout")
        admin_login = self.client.post("/api/v1/auth/login", json={
            "email": "admin@example.edu",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        self.assertEqual(admin_login.status_code, 200)
        admin_complaints = self.client.get("/api/v1/complaints")
        self.assertEqual(admin_complaints.status_code, 200)
        self.assertEqual(len(admin_complaints.json["complaints"]), 2)

    def test_admin_can_anonymize_account_without_removing_complaint_history(self):
        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Admin",
            "email": "admin@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        self.client.post("/api/v1/auth/logout")
        self.client.post("/api/v1/auth/register", json={
            "full_name": "Account to Delete",
            "email": "delete-me@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@example.edu").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            target = User.query.filter_by(email="delete-me@example.edu").one()
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
            "email": "admin@example.edu",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        self.assertEqual(login.status_code, 200)
        deleted = self.client.delete(f"/api/v1/admin/users/{target_id}")
        self.assertEqual(deleted.status_code, 200)
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
        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Admin",
            "email": "admin@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        self.client.post("/api/v1/auth/logout")
        registered = self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Student",
            "email": "student@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "STUDENT",
        })
        target_id = registered.json["user"]["id"]
        self.client.post("/api/v1/auth/logout")
        with self.app.app_context():
            admin = User.query.filter_by(email="admin@example.edu").one()
            admin.role = Role.query.filter_by(name="ADMIN").one()
            db.session.commit()

        self.client.post("/api/v1/auth/login", json={
            "email": "admin@example.edu",
            "password": "A-strong-demo-password",
            "portal": "admin",
        })
        changed = self.client.patch(
            f"/api/v1/admin/users/{target_id}/role",
            json={"role": "OFFICER", "department": "PLUMBING"},
        )
        self.assertEqual(changed.status_code, 200)
        events = self.client.get("/api/v1/admin/audit").json["events"]
        role_event = next(event for event in events if event["action"] == "USER_ROLE_UPDATED")
        self.assertTrue(role_event["can_rollback"])
        self.assertEqual(role_event["old_values"]["role"], "CITIZEN")
        with self.app.app_context():
            legacy_event = db.session.get(AuditLog, role_event["id"])
            legacy_event.old_values = None
            db.session.commit()
        events = self.client.get("/api/v1/admin/audit").json["events"]
        role_event = next(event for event in events if event["id"] == role_event["id"])
        self.assertTrue(role_event["can_rollback"])

        rolled_back = self.client.post(
            f"/api/v1/admin/audit/{role_event['id']}/rollback",
            json={},
        )
        self.assertEqual(rolled_back.status_code, 200)
        self.assertEqual(rolled_back.json["user"]["role"], "CITIZEN")
        self.assertIsNone(rolled_back.json["user"]["department"])
        events = self.client.get("/api/v1/admin/audit").json["events"]
        self.assertFalse(next(event for event in events if event["id"] == role_event["id"])["can_rollback"])
        self.assertEqual(
            self.client.post(f"/api/v1/admin/audit/{role_event['id']}/rollback", json={}).status_code,
            409,
        )

    def test_complaint_creation_and_status_workflow_follow_database_states(self):
        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Citizen",
            "email": "citizen@example.edu",
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

        self.client.post("/api/v1/auth/register", json={
            "full_name": "Test Officer",
            "email": "assigned-officer@example.edu",
            "password": "A-strong-demo-password",
            "user_type": "WORKING_STAFF",
        })
        with self.app.app_context():
            officer = User.query.filter_by(email="assigned-officer@example.edu").one()
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


if __name__ == "__main__":
    unittest.main()
