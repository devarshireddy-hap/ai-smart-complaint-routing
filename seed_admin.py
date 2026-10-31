"""Interactively create or promote the first administrator account."""

from getpass import getpass

from werkzeug.security import generate_password_hash

from backend.app import app
from backend.models import AuditLog, Role, User, db


def main():
    email = input("Administrator email: ").strip().lower()
    full_name = input("Administrator name: ").strip()
    password = getpass("Administrator password (10+ characters): ")
    if "@" not in email or len(full_name) < 2 or len(password) < 10:
        raise ValueError("Enter a valid email, a name, and a password of at least 10 characters.")
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, full_name=full_name, user_type="WORKING_STAFF")
            db.session.add(user)
        user.password_hash = generate_password_hash(password, method="scrypt")
        user.role = Role.query.filter_by(name="ADMIN").one()
        user.department = None
        user.is_active = True
        db.session.flush()
        db.session.add(AuditLog(
            actor_id=user.id,
            action="INITIAL_ADMIN_BOOTSTRAPPED",
            resource_type="user",
            resource_id=user.id,
            details={"role": "ADMIN"},
        ))
        db.session.commit()
        print(f"Administrator ready: {user.email}")


if __name__ == "__main__":
    main()
