import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.audit.models import AuditLog
from app.auth.dependencies import CurrentAdmin, Database

router = APIRouter(prefix="/admin", tags=["Administration"])


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: str
    actor_type: str
    created_at: datetime


@router.get("/activity", response_model=list[ActivityResponse])
def activity(admin: CurrentAdmin, db: Database):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20)).all()
