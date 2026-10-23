import unittest

from backend.app import create_app
from backend.models import Role, User, db


class AuthenticationAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "APP_ENV": "test",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_COOKIE_CSRF_PROTECT": False,
            "JWT_COOKIE_SECURE": False,
            "SECRET_KEY": "test-secret-key",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "FRONTEND_URL": "http://localhost:5173",
            "ENABLE_GEMINI": False,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

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

    def test_officer_can_access_the_department_queue(self):
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
        self.assertEqual(response.json["complaints"], [])


if __name__ == "__main__":
    unittest.main()
