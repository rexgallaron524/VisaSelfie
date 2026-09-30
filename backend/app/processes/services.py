import json
import math
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.core.config import Settings
from app.core.security import hash_token, new_token, utcnow
from app.processes.models import ClientProcess, ConsentRecord, RegistrationLink
from app.processes.schemas import CONSENT_VERSION, ProcessSummary


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def audit(db: Session, process: ClientProcess, action: str, actor_id=None, actor="admin"):
    db.add(
        AuditLog(
            actor_type=actor,
            actor_id=actor_id,
            action=action,
            entity_type="client_process",
            entity_id=process.id,
        )
    )


def process_by_id(db: Session, process_id: uuid.UUID, lock=False) -> ClientProcess:
    query = select(ClientProcess).where(ClientProcess.id == process_id)
    if lock:
        query = query.with_for_update()
    process = db.scalar(query.execution_options(populate_existing=True))
    if not process:
        raise HTTPException(404, "Client process not found.")
    return process


def latest_link(db: Session, process_id: uuid.UUID):
    return db.scalar(
        select(RegistrationLink)
        .where(RegistrationLink.client_process_id == process_id)
        .order_by(RegistrationLink.created_at.desc())
        .limit(1)
    )


def summary(db: Session, process: ClientProcess) -> ProcessSummary:
    link = latest_link(db, process.id)
    status = process.status
    if link and link.status == "active" and aware(link.expires_at) <= utcnow():
        status = "expired"
    return ProcessSummary(
        id=process.id,
        full_name=process.full_name,
        phone_number=process.phone_number,
        status=status,
        created_at=process.created_at,
        updated_at=process.updated_at,
        link_expires_at=link.expires_at if link else None,
    )


def issue_link(db: Session, process: ClientProcess, admin_id, settings: Settings):
    if process.status in {"submitted", "reviewed", "deleted"}:
        raise HTTPException(409, "This process is closed. Create a new process for another video.")
    for link in db.scalars(
        select(RegistrationLink).where(
            RegistrationLink.client_process_id == process.id, RegistrationLink.status == "active"
        )
    ):
        link.status = "revoked"
    token = new_token()
    expires = utcnow() + timedelta(hours=48)
    db.add(
        RegistrationLink(
            client_process_id=process.id, token_hash=hash_token(token), expires_at=expires
        )
    )
    if process.status in {"created", "opened", "link_generated"}:
        process.status = "link_generated"
    process.updated_at = utcnow()
    audit(db, process, "link.generated", admin_id)
    return {
        "process_id": process.id,
        "token": token,
        "registration_url": f"{settings.frontend_public_url}/register/{token}",
        "expires_at": expires,
    }


def applicant(db: Session, authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(404, "This registration link is invalid.")
    token = authorization[7:]
    if not 20 <= len(token) <= 128:
        raise HTTPException(404, "This registration link is invalid.")
    link = db.scalar(
        select(RegistrationLink).where(RegistrationLink.token_hash == hash_token(token))
    )
    if not link:
        raise HTTPException(404, "This registration link is invalid.")
    # Serialize all mutations for a process, including regeneration and final upload.
    process = process_by_id(db, link.client_process_id, lock=True)
    db.refresh(link)
    if link.status == "revoked":
        raise HTTPException(404, "This registration link has been replaced. Ask for a new link.")
    if link.used_at or process.status in {"submitted", "reviewed", "deleted"}:
        raise HTTPException(409, "This recording has already been submitted.")
    if aware(link.expires_at) <= utcnow():
        raise HTTPException(
            410, "This registration link has expired. Ask the operator for a new link."
        )
    return process, link


def consent_for(db: Session, process_id: uuid.UUID):
    return db.scalar(
        select(ConsentRecord)
        .where(
            ConsentRecord.client_process_id == process_id,
            ConsentRecord.consent_version == CONSENT_VERSION,
        )
        .order_by(ConsentRecord.accepted_at.desc())
        .limit(1)
    )


def inspect_video(path: Path, declared_mime: str, settings: Settings):
    """Read actual packets: browser WebM often has no container duration header."""
    try:
        result = subprocess.run(
            [
                settings.ffprobe_path,
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_name,width,height:format=format_name:packet=pts_time,duration_time",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            timeout=20,
            check=True,
        )
        info = json.loads(result.stdout)
        stream = info.get("streams", [{}])[0]
        format_name = info.get("format", {}).get("format_name", "")
        valid_format = (declared_mime == "video/webm" and "webm" in format_name) or (
            declared_mime == "video/mp4" and "mp4" in format_name
        )
        if not valid_format or stream.get("codec_name") not in {"vp8", "vp9", "h264", "av1"}:
            raise ValueError
        if not 64 <= stream.get("width", 0) <= 3840 or not 64 <= stream.get("height", 0) <= 3840:
            raise ValueError
        packets = info.get("packets", [])
        starts = [float(p["pts_time"]) for p in packets if "pts_time" in p]
        ends = [
            float(p["pts_time"]) + float(p.get("duration_time", 0))
            for p in packets
            if "pts_time" in p
        ]
        duration = max(ends) - min(starts)
        if not math.isfinite(duration) or not 2.5 <= duration <= settings.max_video_seconds + 1:
            raise ValueError
        return round(duration, 3)
    except FileNotFoundError:
        raise HTTPException(
            503, "Video validation is unavailable. Please contact the operator."
        ) from None
    except (subprocess.SubprocessError, ValueError, KeyError, IndexError):
        raise HTTPException(
            422, "Record a valid video between 3 and 30 seconds and try again."
        ) from None
