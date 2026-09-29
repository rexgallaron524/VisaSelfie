from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete, select

from app.audit.models import AuditLog
from app.auth.dependencies import CurrentAdmin, Database
from app.auth.models import AdminSession, AdminUser
from app.auth.schemas import AdminResponse, LoginRequest
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    SESSION_COOKIE,
    hash_token,
    new_token,
    password_hasher,
    utcnow,
)
from app.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=AdminResponse)
@limiter.limit("5/minute")
def login(request: Request, response: Response, payload: LoginRequest, db: Database):
    admin = db.scalar(select(AdminUser).where(AdminUser.email == str(payload.email).lower()))
    valid, updated_hash = password_hasher.verify_and_update(
        payload.password, admin.password_hash if admin else DUMMY_PASSWORD_HASH
    )
    if not admin or not valid or not admin.is_active:
        db.add(
            AuditLog(actor_type="anonymous", action="admin.login_failed", entity_type="admin_user")
        )
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect.")

    settings = request.app.state.settings
    now = utcnow()
    db.execute(delete(AdminSession).where(AdminSession.expires_at <= now))
    old_token = request.cookies.get(SESSION_COOKIE)
    if old_token:
        db.execute(delete(AdminSession).where(AdminSession.token_hash == hash_token(old_token)))
    token = new_token()
    db.add(
        AdminSession(
            admin_id=admin.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(hours=settings.session_hours),
        )
    )
    if updated_hash:
        admin.password_hash = updated_hash
    admin.last_login = now
    db.add(
        AuditLog(
            actor_type="admin",
            actor_id=admin.id,
            action="admin.login",
            entity_type="admin_user",
            entity_id=admin.id,
        )
    )
    db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return admin


@router.get("/me", response_model=AdminResponse)
def me(admin: CurrentAdmin):
    return admin


@router.post("/logout", status_code=204)
def logout(request: Request, db: Database):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = db.scalar(
            select(AdminSession).where(AdminSession.token_hash == hash_token(token))
        )
        if session:
            db.add(
                AuditLog(
                    actor_type="admin",
                    actor_id=session.admin_id,
                    action="admin.logout",
                    entity_type="admin_user",
                    entity_id=session.admin_id,
                )
            )
            db.delete(session)
            db.commit()
    response = Response(status_code=204)
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=request.app.state.settings.cookie_secure,
        samesite="lax",
    )
    return response
