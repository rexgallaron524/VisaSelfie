from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import AdminSession, AdminUser
from app.core.database import get_db
from app.core.security import SESSION_COOKIE, hash_token, utcnow

Database = Annotated[Session, Depends(get_db)]


def require_admin(request: Request, db: Database) -> AdminUser:
    token = request.cookies.get(SESSION_COOKIE)
    if token and len(token) <= 128:
        admin = db.scalar(
            select(AdminUser)
            .join(AdminSession, AdminSession.admin_id == AdminUser.id)
            .where(
                AdminSession.token_hash == hash_token(token),
                AdminSession.expires_at > utcnow(),
                AdminUser.is_active.is_(True),
            )
        )
        if admin:
            return admin
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in to continue.")


CurrentAdmin = Annotated[AdminUser, Depends(require_admin)]
