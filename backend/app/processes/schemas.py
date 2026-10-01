import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONSENT_VERSION = "2026-09-30-video-checks"
CONSENT_TEXT = (
    "I agree that the operator who sent me this link may collect my name, date of birth, "
    "passport number, phone number, and facial video to manage my visa verification process. "
    "The video and my details are stored privately and can be accessed by authorized "
    "administrators. My consent time, connection IP address, and browser information are "
    "recorded for auditing. The operator can download or delete the video and retains it "
    "until it is no longer needed. I can contact the operator who invited me to ask about "
    "retention or request deletion. This service does not automatically submit my recording "
    "to an embassy or visa authority. Automated checks evaluate lighting, face framing, "
    "sharpness and prompted movements on our server. They do not verify my identity or "
    "guarantee liveness; an administrator must review the recording. No facial identity "
    "template is retained. I understand and consent to this collection and use."
)


class ClientFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    full_name: str = Field(min_length=2, max_length=200)
    phone_number: str = Field(min_length=7, max_length=32)

    @field_validator("phone_number")
    @classmethod
    def valid_phone(cls, value: str):
        if (
            not re.fullmatch(r"\+?[0-9 ()-]+", value)
            or not 7 <= len(re.sub(r"\D", "", value)) <= 15
        ):
            raise ValueError("Enter a phone number with 7–15 digits, including country code")
        return value


class CreateProcess(ClientFields):
    pass


class Registration(ClientFields):
    date_of_birth: date
    passport_number: str = Field(min_length=5, max_length=32, pattern=r"^[A-Za-z0-9 -]+$")

    @field_validator("date_of_birth")
    @classmethod
    def valid_dob(cls, value: date):
        if value < date(1900, 1, 1) or value > date.today():
            raise ValueError("Enter a valid date of birth")
        return value


class ConsentInput(BaseModel):
    accepted: bool
    version: str


class ProcessSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    phone_number: str
    status: str
    created_at: datetime
    updated_at: datetime
    link_expires_at: datetime | None


class LinkIssued(BaseModel):
    process_id: uuid.UUID
    token: str
    registration_url: str
    expires_at: datetime


class VideoInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    mime_type: str
    file_size: int
    duration: float
    uploaded_at: datetime
    deleted_at: datetime | None
    status: str
    assessment: dict | None = None


class EventInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    action: str
    actor_type: str
    created_at: datetime


class ConsentInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    consent_version: str
    accepted_at: datetime


class ProcessDetail(ProcessSummary):
    date_of_birth: date | None
    passport_number: str | None
    consent: ConsentInfo | None
    video: VideoInfo | None
    history: list[EventInfo]


class PublicState(BaseModel):
    full_name: str
    phone_number: str
    registered: bool
    consent_accepted: bool
    expires_at: datetime
    consent_version: str = CONSENT_VERSION
    consent_text: str = CONSENT_TEXT
    max_upload_bytes: int
    max_video_seconds: int
