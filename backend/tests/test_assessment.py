import copy
import subprocess
from datetime import timedelta
from itertools import permutations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.security import utcnow
from app.processes.assessment import ACTIONS, assess_video, evaluate_samples
from app.processes.models import RecordingChallenge, RegistrationLink, VideoSubmission
from tests.test_processes import create, prepare, upload
from tests.test_processes import store as store_fixture

store = store_fixture


def trace(actions=ACTIONS):
    """Synthetic inference outputs; these tests do not measure biometric accuracy."""
    samples = [
        dict(
            t=i / 10,
            faces=1,
            framed=True,
            lighting=True,
            sharp=True,
            blink=0.05,
            jaw=0.05,
            turn=0.5,
        )
        for i in range(180)
    ]
    for index, action in enumerate(actions):
        field, value = {
            "blink": ("blink", 0.9),
            "open_mouth": ("jaw", 0.8),
            "turn_head": ("turn", 0.8),
        }[action]
        for sample in samples:
            if 3 + 5 * index <= sample["t"] < 4 + 5 * index:
                sample[field] = value
    return samples


@pytest.mark.parametrize("actions", list(permutations(ACTIONS)))
def test_all_prompt_orders(actions):
    report = evaluate_samples(trace(actions), actions)
    assert report["passed"]
    assert report["liveness"] == "not_verified"
    assert report["manual_review_required"]


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("faces", 0, "one_face"),
        ("faces", 2, "one_face"),
        ("framed", False, "framing"),
        ("lighting", False, "lighting"),
        ("sharp", False, "sharpness"),
    ],
)
def test_quality_failures(field, value, code):
    samples = trace()
    for s in samples:
        s[field] = value
    report = evaluate_samples(samples, ACTIONS)
    assert not report["passed"]
    assert any(c["code"] == code and not c["passed"] for c in report["checks"])


def test_static_photo_motion_wrong_order_and_incomplete_recording_fail():
    still = [dict(s, blink=0.05, jaw=0.05, turn=0.5) for s in trace()]
    assert not evaluate_samples(still, ACTIONS)["passed"]
    # Translating a still photo does not supply the prompted expression transitions.
    moved = [dict(s, turn=0.8 if i % 10 < 5 else 0.5) for i, s in enumerate(still)]
    assert not evaluate_samples(moved, ACTIONS)["passed"]
    assert not evaluate_samples(trace(), tuple(reversed(ACTIONS)))["passed"]
    assert not evaluate_samples(trace()[:100], ACTIONS)["passed"]
    assert not evaluate_samples([], ACTIONS)["passed"]


def test_no_return_to_neutral_fails():
    samples = trace()
    for s in samples:
        if s["t"] >= 3:
            s["blink"] = 0.9
    assert not evaluate_samples(samples, ACTIONS)["passed"]


def test_quality_failure_does_not_store_or_consume_link(client, db, store, monkeypatch):
    _, headers = create(client)
    prepare(client, headers)
    report = evaluate_samples([], ACTIONS)
    monkeypatch.setattr("app.processes.routes.assess_video", lambda *args: report)
    result = upload(client, headers)
    assert result.status_code == 422
    assert result.json()["detail"]["assessment"] == report
    assert not store.objects
    assert db.scalar(select(VideoSubmission)) is None
    assert db.scalar(select(RegistrationLink)).used_at is None


@pytest.mark.parametrize("invalid", ["missing", "wrong", "expired", "early", "replaced"])
def test_challenge_is_bound_to_recording(client, db, store, invalid):
    _, headers = create(client)
    prepare(client, headers)
    challenge = db.scalar(select(RecordingChallenge))
    if invalid == "missing":
        headers.pop("X-Recording-Challenge")
    elif invalid == "wrong":
        headers["X-Recording-Challenge"] = "00000000-0000-0000-0000-000000000000"
    elif invalid == "expired":
        challenge.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    elif invalid == "early":
        challenge.created_at = utcnow()
        db.commit()
    else:
        result = client.post("/api/public/recording", headers=headers)
        assert result.status_code == 200
        assert result.json()["id"] != headers["X-Recording-Challenge"]
    assert upload(client, headers).status_code in (409, 422)
    assert not store.objects


def test_challenge_and_link_rechecked_after_analysis(client, db, store, monkeypatch):
    _, headers = create(client)
    prepare(client, headers)

    def expire(*args):
        db.scalar(select(RecordingChallenge)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        return {"passed": True}

    monkeypatch.setattr("app.processes.routes.assess_video", expire)
    assert upload(client, headers).status_code == 409
    assert not store.objects


def test_success_saves_summary_not_landmarks(client, db, store):
    _, headers = create(client)
    prepare(client, headers)
    assert upload(client, headers).status_code == 201
    report = db.scalar(select(VideoSubmission)).assessment
    assert report["liveness"] == "not_verified"
    assert "landmarks" not in report
    assert upload(client, headers).status_code == 409


def test_replacement_link_cannot_reuse_previous_recording(client, db, store):
    issued, headers = create(client)
    prepare(client, headers)
    replacement = client.post(f"/api/admin/processes/{issued['process_id']}/link").json()
    headers["Authorization"] = f"Bearer {replacement['token']}"
    assert upload(client, headers).status_code == 409
    assert not store.objects


def test_link_expiration_during_inference_is_enforced(client, db, store, monkeypatch):
    _, headers = create(client)
    prepare(client, headers)

    def expire(*args):
        db.scalar(select(RegistrationLink)).expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
        return {"passed": True}

    monkeypatch.setattr("app.processes.routes.assess_video", expire)
    assert upload(client, headers).status_code == 410
    assert not store.objects


def test_short_decoded_video_is_rejected(client, store, monkeypatch):
    _, headers = create(client)
    prepare(client, headers)
    monkeypatch.setattr("app.processes.routes.inspect_video", lambda *args: 4.0)
    assert upload(client, headers).status_code == 422
    assert not store.objects


def test_validation_unavailable_fails_closed(client, db, store, monkeypatch):
    _, headers = create(client)
    prepare(client, headers)

    def unavailable(*args):
        raise HTTPException(503, "Checks unavailable")

    monkeypatch.setattr("app.processes.routes.assess_video", unavailable)
    assert upload(client, headers).status_code == 503
    assert not store.objects
    assert db.scalar(select(RegistrationLink)).used_at is None


def test_worker_timeout_and_corrupt_output_fail_closed(monkeypatch, tmp_path):
    from app.core.config import Settings

    config = Settings(_env_file=None, database_url="sqlite://", app_env="test")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("worker", 90)

    monkeypatch.setattr("app.processes.assessment.subprocess.run", timeout)
    with pytest.raises(HTTPException) as e:
        assess_video(tmp_path / "video", ACTIONS, config)
    assert e.value.status_code == 503
    monkeypatch.setattr(
        "app.processes.assessment.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess([], 0, b"not json"),
    )
    with pytest.raises(HTTPException) as e:
        assess_video(tmp_path / "video", ACTIONS, config)
    assert e.value.status_code == 503


def test_image_metrics_detect_dark_bright_blur_and_cropping():
    from types import SimpleNamespace as NS

    import numpy as np

    from app.processes.face_worker import frame_sample

    points = [NS(x=0.3, y=0.25) for _ in range(478)]
    points[1] = NS(x=0.5, y=0.5)
    points[234] = NS(x=0.3, y=0.25)
    points[454] = NS(x=0.7, y=0.75)
    result = NS(face_landmarks=[points], face_blendshapes=[[]])
    for brightness in (10, 250):
        sample = frame_sample(np.full((480, 480, 3), brightness, dtype=np.uint8), result, 0)
        assert not sample["lighting"]
    sample = frame_sample(np.full((480, 480, 3), 120, dtype=np.uint8), result, 0)
    assert sample["lighting"] and not sample["sharp"]
    cropped = copy.deepcopy(result)
    cropped.face_landmarks[0][10].y = -0.01
    sample = frame_sample(np.full((480, 480, 3), 120, dtype=np.uint8), cropped, 0)
    assert not sample["framed"]


def test_real_model_detects_photo_but_does_not_accept_it_as_guided_video():
    from pathlib import Path

    import cv2
    import mediapipe as mp
    import numpy as np

    from app.processes.face_worker import frame_sample

    model = Path(__file__).parents[1] / "models" / "face_landmarker.task"
    if not model.exists():
        pytest.skip("Run python download_face_model.py to test real inference")
    photo = cv2.imread(str(Path(__file__).parent / "fixtures" / "astronaut.png"))
    face = cv2.resize(photo[10:250, 120:340], (440, 480))
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        num_faces=2,
        output_face_blendshapes=True,
        min_face_detection_confidence=0.6,
        min_face_presence_confidence=0.6,
    )
    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:

        def sample(frame):
            result = detector.detect(
                mp.Image(
                    image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                )
            )
            return frame_sample(frame, result, 0)

        still = sample(face)
        assert still["faces"] == 1
        assert still["framed"] and still["lighting"] and still["sharp"]
        report = evaluate_samples([dict(still, t=i / 10) for i in range(180)], ACTIONS)
        assert not report["passed"]
        assert not any(c["passed"] for c in report["checks"] if c["code"] in ACTIONS)
        assert sample(np.zeros_like(face))["faces"] == 0
        pair = np.concatenate([cv2.resize(face, (220, 240))] * 2, axis=1)
        assert sample(pair)["faces"] == 2
