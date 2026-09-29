import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.audit.models import AuditLog
from app.auth.models import AdminUser
from app.core.database import get_session_factory
from app.core.security import password_hasher


def main():
    parser = argparse.ArgumentParser(description="Visa Selfie administration")
    parser.add_argument("command", choices=["create-admin"])
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    except ValidationError:
        parser.error("Provide a valid email address")
    if len(email) > 254:
        parser.error("Email address is too long")
    password = getpass("Password (12–128 characters): ")
    if not 12 <= len(password) <= 128:
        parser.error("Password must have 12–128 characters")
    if password != getpass("Confirm password: "):
        parser.error("Passwords do not match")
    with get_session_factory()() as db:
        if db.scalar(select(AdminUser).where(AdminUser.email == email)):
            parser.error("An administrator with this email already exists")
        admin = AdminUser(email=email, password_hash=password_hasher.hash(password))
        db.add(admin)
        db.flush()
        db.add(
            AuditLog(
                actor_type="system",
                action="admin.created",
                entity_type="admin_user",
                entity_id=admin.id,
            )
        )
        db.commit()
    print("Administrator created. You can now sign in.")


if __name__ == "__main__":
    main()
