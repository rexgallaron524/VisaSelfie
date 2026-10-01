import re
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, case, func, select
from starlette.concurrency import run_in_threadpool

from app.audit.models import AuditLog
from app.auth.dependencies import CurrentAdmin, Database
from app.core.security import utcnow
from app.limiter import limiter
from app.processes.assessment import (
    CHALLENGE_SECONDS,
    RECORDING_SECONDS,
    assess_video,
    challenge_payload,
    new_actions,
)
from app.processes.models import (
    ClientProcess,
    ConsentRecord,
    RecordingChallenge,
    RegistrationLink,
    VideoSubmission,
)
from app.processes.schemas import (
    CONSENT_VERSION,
    ConsentInput,
    CreateProcess,
    LinkIssued,
    ProcessDetail,
    ProcessSummary,
    PublicState,
    Registration,
)
from app.processes.services import (
    applicant,
    audit,
    aware,
    consent_for,
    inspect_video,
    issue_link,
    process_by_id,
    summary,
)
from app.storage import ObjectStore, get_store

router = APIRouter(tags=["Client processes"])
Store = Annotated[ObjectStore, Depends(get_store)]
Authorization = Annotated[str | None, Header()]


def listing_query():
    expires = (
        select(
            RegistrationLink.client_process_id,
            func.max(RegistrationLink.expires_at).label("expires"),
        )
        .where(RegistrationLink.status != "revoked")
        .group_by(RegistrationLink.client_process_id)
        .subquery()
    )
    state = case(
        (
            and_(
                expires.c.expires <= utcnow(),
                ClientProcess.status.not_in(["submitted", "reviewed", "deleted"]),
            ),
            "expired",
        ),
        else_=ClientProcess.status,
    ).label("effective_status")
    return select(ClientProcess, expires.c.expires, state).outerjoin(
        expires, expires.c.client_process_id == ClientProcess.id
    ), state


@router.get("/admin/processes/summary")
def overview(admin: CurrentAdmin, db: Database):
    query, _ = listing_query()
    sub = query.subquery()
    counts = dict(
        db.execute(
            select(sub.c.effective_status, func.count()).group_by(sub.c.effective_status)
        ).all()
    )
    return {
        "total_clients": sum(counts.values()),
        "pending_registration": sum(
            counts.get(s, 0) for s in ["created", "link_generated", "opened"]
        ),
        "submitted_videos": counts.get("submitted", 0) + counts.get("reviewed", 0),
        "expired_links": counts.get("expired", 0),
    }


@router.get("/admin/processes")
def list_processes(
    admin: CurrentAdmin,
    db: Database,
    q: str = Query(default="", max_length=200),
    status: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    query, state = listing_query()
    if q.strip():
        query = query.where(ClientProcess.full_name.icontains(q.strip(), autoescape=True))
    if status:
        query = query.where(state == status)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.execute(
        query.order_by(ClientProcess.updated_at.desc(), ClientProcess.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            ProcessSummary(
                id=p.id,
                full_name=p.full_name,
                phone_number=p.phone_number,
                status=s,
                created_at=p.created_at,
                updated_at=p.updated_at,
                link_expires_at=expiry,
            )
            for p, expiry, s in rows
        ],
    }


@router.post("/admin/processes", response_model=LinkIssued, status_code=201)
def create_process(request: Request, payload: CreateProcess, admin: CurrentAdmin, db: Database):
    process = ClientProcess(**payload.model_dump())
    db.add(process)
    db.flush()
    audit(db, process, "process.created", admin.id)
    result = issue_link(db, process, admin.id, request.app.state.settings)
    db.commit()
    return result


@router.get("/admin/processes/{process_id}", response_model=ProcessDetail)
def detail(process_id: uuid.UUID, admin: CurrentAdmin, db: Database):
    process = process_by_id(db, process_id)
    audit(db, process, "process.viewed", admin.id)
    db.commit()
    return ProcessDetail(
        **summary(db, process).model_dump(),
        date_of_birth=process.date_of_birth,
        passport_number=process.passport_number,
        email=process.email,
        alternative_phone_number=process.alternative_phone_number,
        address=process.address,
        consent=consent_for(db, process.id),
        video=db.scalar(
            select(VideoSubmission).where(VideoSubmission.client_process_id == process.id)
        ),
        history=db.scalars(
            select(AuditLog)
            .where(AuditLog.entity_id == process.id)
            .order_by(AuditLog.created_at.desc())
            .limit(100)
        ).all(),
    )


@router.post("/admin/processes/{process_id}/link", response_model=LinkIssued)
def regenerate(request: Request, process_id: uuid.UUID, admin: CurrentAdmin, db: Database):
    process = process_by_id(db, process_id, lock=True)
    result = issue_link(db, process, admin.id, request.app.state.settings)
    db.commit()
    return result


@router.post("/public/open", response_model=PublicState)
def open_link(request: Request, db: Database, authorization: Authorization = None):
    process, link = applicant(db, authorization)
    if not link.opened_at:
        link.opened_at = utcnow()
        if process.status == "link_generated":
            process.status = "opened"
        process.updated_at = utcnow()
        audit(db, process, "link.opened", actor="applicant", actor_id=process.id)
    result = PublicState(
        full_name=process.full_name,
        phone_number=process.phone_number,
        expires_at=link.expires_at,
        registered=process.date_of_birth is not None,
        consent_accepted=consent_for(db, process.id) is not None,
        max_upload_bytes=request.app.state.settings.max_upload_bytes,
        max_video_seconds=request.app.state.settings.max_video_seconds,
    )
    db.commit()
    return result


@router.post("/public/register", status_code=204)
def register(payload: Registration, db: Database, authorization: Authorization = None):
    process, _ = applicant(db, authorization)
    if consent_for(db, process.id):
        raise HTTPException(
            409, "Registration is already confirmed. Contact your operator to correct it."
        )
    if re.sub(r"\D", "", payload.phone_number) != re.sub(r"\D", "", process.phone_number):
        raise HTTPException(
            422,
            "This phone number does not match your invitation. Reload the page and try again. "
            "If the displayed number is incorrect, contact the operator who sent you the link.",
        )
    for key, value in payload.model_dump(exclude={"phone_number"}).items():
        setattr(process, key, value)
    process.status = "registered"
    process.updated_at = utcnow()
    audit(db, process, "client.registered", actor="applicant", actor_id=process.id)
    db.commit()


@router.post("/public/consent", status_code=204)
def consent(
    request: Request, payload: ConsentInput, db: Database, authorization: Authorization = None
):
    process, _ = applicant(db, authorization)
    if not process.date_of_birth:
        raise HTTPException(409, "Complete registration first.")
    if not payload.accepted or payload.version != CONSENT_VERSION:
        raise HTTPException(422, "You must accept the current privacy notice to record.")
    if not consent_for(db, process.id):
        db.add(
            ConsentRecord(
                client_process_id=process.id,
                consent_version=CONSENT_VERSION,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown")[:512],
            )
        )
        audit(db, process, "consent.accepted", actor="applicant", actor_id=process.id)
        process.updated_at = utcnow()
    db.commit()


def recording_allowed(db, process):
    if not process.date_of_birth or not consent_for(db, process.id):
        raise HTTPException(409, "Complete registration and accept consent before recording.")


@router.post("/public/recording")
@limiter.limit("6/minute")
def recording(request: Request, db: Database, authorization: Authorization = None):
    process, link = applicant(db, authorization)
    recording_allowed(db, process)
    if request.app.state.settings.max_video_seconds < RECORDING_SECONDS:
        raise HTTPException(503, "Guided recording is not configured. Contact your operator.")
    challenge = db.scalar(
        select(RecordingChallenge).where(RecordingChallenge.client_process_id == process.id)
    )
    if challenge is None:
        challenge = RecordingChallenge(client_process_id=process.id)
        db.add(challenge)
    challenge.id = uuid.uuid4()
    challenge.registration_link_id = link.id
    challenge.actions = new_actions()
    challenge.created_at = utcnow()
    challenge.expires_at = min(
        utcnow() + timedelta(seconds=CHALLENGE_SECONDS), aware(link.expires_at)
    )
    process.status = "recording_started"
    process.updated_at = utcnow()
    audit(db, process, "recording.started", actor="applicant", actor_id=process.id)
    db.commit()
    return challenge_payload(challenge)


def validate_challenge(db, process, link, challenge_id):
    challenge = db.scalar(
        select(RecordingChallenge).where(RecordingChallenge.client_process_id == process.id)
    )
    if (
        not challenge
        or str(challenge.id) != challenge_id
        or challenge.registration_link_id != link.id
    ):
        raise HTTPException(409, "Recording instructions changed. Please retake your video.")
    if aware(challenge.expires_at) <= utcnow():
        raise HTTPException(409, "Recording session expired. Please retake your video.")
    return challenge


def finish_upload(db, authorization, store, path, size, mime, settings, challenge_id):
    process, link = applicant(db, authorization)
    recording_allowed(db, process)
    if process.status != "recording_started":
        raise HTTPException(409, "Start a recording before submitting.")
    challenge = validate_challenge(db, process, link, challenge_id)
    actions = list(challenge.actions)
    if (utcnow() - aware(challenge.created_at)).total_seconds() < RECORDING_SECONDS - 1:
        raise HTTPException(422, "Complete the full guided recording before submitting.")
    # Do not hold a database row lock during expensive media processing.
    db.rollback()
    duration = inspect_video(path, mime, settings)
    if not RECORDING_SECONDS - 1 <= duration <= RECORDING_SECONDS + 1:
        raise HTTPException(422, "Record the full 18-second guided sequence and try again.")
    assessment = assess_video(path, actions, settings)
    # Re-check expiry, consent, replacement, and concurrent submissions after inference.
    process, link = applicant(db, authorization)
    recording_allowed(db, process)
    validate_challenge(db, process, link, challenge_id)
    if not assessment["passed"]:
        audit(db, process, "video.checks_failed", actor="applicant", actor_id=process.id)
        db.commit()
        raise HTTPException(
            422,
            detail={
                "message": "Please retake your recording using the guidance below.",
                "assessment": assessment,
            },
        )
    extension = "webm" if mime == "video/webm" else "mp4"
    key = f"videos/{process.id}/{uuid.uuid4()}.{extension}"
    try:
        with path.open("rb") as file:
            store.put(key, file, size, mime)
        db.add(
            VideoSubmission(
                client_process_id=process.id,
                storage_key=key,
                original_filename=f"recording.{extension}",
                mime_type=mime,
                file_size=size,
                duration=duration,
                assessment=assessment,
            )
        )
        process.status = "submitted"
        process.updated_at = utcnow()
        link.used_at = utcnow()
        link.status = "used"
        audit(db, process, "video.submitted", actor="applicant", actor_id=process.id)
        db.commit()
    except Exception:
        db.rollback()
        # Best-effort cleanup, with no falsely successful submission on storage errors.
        try:
            store.delete(key)
        except (BotoCoreError, ClientError):
            pass
        raise
    return {"status": "submitted"}


@router.post("/public/video", status_code=201)
@limiter.limit("6/minute")
async def upload(request: Request, db: Database, store: Store, authorization: Authorization = None):
    # Authenticate before accepting any body; release the lock while receiving bytes.
    process, link = await run_in_threadpool(applicant, db, authorization)
    recording_allowed(db, process)
    challenge_id = request.headers.get("x-recording-challenge", "")
    if not challenge_id or len(challenge_id) > 36:
        raise HTTPException(409, "Start a new guided recording before submitting.")
    validate_challenge(db, process, link, challenge_id)
    db.rollback()
    settings = request.app.state.settings
    mime = request.headers.get("content-type", "").split(";")[0].lower()
    if mime not in {"video/webm", "video/mp4"}:
        raise HTTPException(415, "Only WebM or MP4 recordings are accepted.")
    declared = request.headers.get("content-length")
    if declared and (not declared.isdigit() or int(declared) > settings.max_upload_bytes):
        raise HTTPException(413, "Recording is too large. Please record a shorter video.")
    with tempfile.TemporaryDirectory(prefix="visa-upload-") as temp:
        path = Path(temp) / "recording"
        size = 0
        with path.open("wb") as file:
            async for chunk in request.stream():
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        413, "Recording is too large. Please record a shorter video."
                    )
                await run_in_threadpool(file.write, chunk)
        try:
            return await run_in_threadpool(
                finish_upload,
                db,
                authorization,
                store,
                path,
                size,
                mime,
                settings,
                challenge_id,
            )
        except (BotoCoreError, ClientError):
            raise HTTPException(
                503, "Upload could not be stored. Please retry your submission."
            ) from None


def video_for(db, process_id):
    video = db.scalar(
        select(VideoSubmission).where(VideoSubmission.client_process_id == process_id)
    )
    if not video:
        raise HTTPException(404, "No video has been submitted.")
    return video


@router.get("/admin/processes/{process_id}/video")
def video_content(
    process_id: uuid.UUID,
    request: Request,
    admin: CurrentAdmin,
    db: Database,
    store: Store,
    download: bool = False,
):
    process = process_by_id(db, process_id)
    video = video_for(db, process_id)
    if video.status != "active":
        raise HTTPException(410, "This video has been deleted or is being deleted.")
    byte_range = request.headers.get("range")
    if byte_range and not re.fullmatch(r"bytes=(?:\d+-\d*|-\d+)", byte_range):
        raise HTTPException(416, "Invalid video range.")
    try:
        obj = store.get(video.storage_key, byte_range)
    except ClientError as exc:
        status = exc.response["ResponseMetadata"]["HTTPStatusCode"]
        raise HTTPException(
            416 if status == 416 else 503, "Video is temporarily unavailable."
        ) from None
    except BotoCoreError:
        raise HTTPException(503, "Video is temporarily unavailable.") from None
    audit(db, process, "video.downloaded" if download else "video.viewed", admin.id)
    db.commit()

    def chunks():
        try:
            yield from obj["Body"].iter_chunks(chunk_size=64 * 1024)
        finally:
            obj["Body"].close()

    disposition = "attachment" if download else "inline"
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(obj["ContentLength"]),
        "Content-Disposition": f'{disposition}; filename="{video.original_filename}"',
    }
    if "ContentRange" in obj:
        headers["Content-Range"] = obj["ContentRange"]
    return StreamingResponse(
        chunks(),
        status_code=206 if "ContentRange" in obj else 200,
        media_type=video.mime_type,
        headers=headers,
    )


@router.post("/admin/processes/{process_id}/review", status_code=204)
def review(process_id: uuid.UUID, admin: CurrentAdmin, db: Database):
    process = process_by_id(db, process_id, lock=True)
    if video_for(db, process_id).status != "active":
        raise HTTPException(409, "Only an active submitted video can be reviewed.")
    if process.status != "reviewed":
        process.status = "reviewed"
        process.updated_at = utcnow()
        audit(db, process, "video.reviewed", admin.id)
    db.commit()


@router.delete("/admin/processes/{process_id}/video", status_code=204)
def delete_video(process_id: uuid.UUID, admin: CurrentAdmin, db: Database, store: Store):
    process = process_by_id(db, process_id, lock=True)
    video = video_for(db, process_id)
    if video.status == "deleted":
        return Response(status_code=204)
    if video.status != "deleting":
        video.status = "deleting"
        audit(db, process, "video.deletion_requested", admin.id)
    key = video.storage_key
    db.commit()
    try:
        store.delete(key)
    except (BotoCoreError, ClientError):
        raise HTTPException(
            503, "Deletion is pending. Retry to finish removing the video."
        ) from None
    process = process_by_id(db, process_id, lock=True)
    db.refresh(video)
    if video.status != "deleted":
        video.status = "deleted"
        video.deleted_at = utcnow()
        process.status = "deleted"
        process.updated_at = utcnow()
        audit(db, process, "video.deleted", admin.id)
    db.commit()
