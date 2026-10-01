"""Conservative capture-quality checks, not identity matching or certified PAD."""

import json
import random
import subprocess
import sys
import threading

from fastapi import HTTPException

BASELINE_SECONDS = 2
ACTION_SECONDS = 5
RECORDING_SECONDS = 18
CHALLENGE_SECONDS = 300
ACTIONS = ("blink", "open_mouth", "turn_head")
LABELS = {
    "blink": "Slowly close both eyes, then open them",
    "open_mouth": "Open your mouth, then close it",
    "turn_head": "Turn your head slightly to one side, then face forward",
}
# Bound expensive work per API process. Deployment currently uses one API worker.
_slot = threading.BoundedSemaphore(1)


def new_actions():
    return random.SystemRandom().sample(ACTIONS, len(ACTIONS))


def challenge_payload(challenge):
    return {
        "id": str(challenge.id),
        "expires_at": challenge.expires_at.isoformat(),
        "duration_seconds": RECORDING_SECONDS,
        "baseline_seconds": BASELINE_SECONDS,
        "action_seconds": ACTION_SECONDS,
        "actions": [{"key": action, "instruction": LABELS[action]} for action in challenge.actions],
    }


def evaluate_samples(samples, actions):
    """Pure temporal policy, shared by real inference and deterministic tests.

    A movement must go neutral -> requested expression -> neutral within its
    server-selected time window. Motion alone is never labelled proof of liveness.
    """
    checks = []

    def add(code, passed, message):
        checks.append({"code": code, "passed": bool(passed), "message": message})

    count = max(len(samples), 1)
    single = [s for s in samples if s["faces"] == 1]
    usable = [s for s in single if s["framed"] and s["lighting"] and s["sharp"]]
    add(
        "coverage",
        len(samples) >= 170 and samples[-1]["t"] >= 16.9,
        "Complete the full guided recording without pausing or changing tabs.",
    )
    add(
        "one_face",
        len(single) / count >= 0.9 and not any(s["faces"] > 1 for s in samples),
        "Keep exactly one face visible throughout the recording.",
    )
    add(
        "framing",
        sum(s["framed"] for s in single) / count >= 0.85,
        "Keep your forehead, chin and both cheeks inside the frame; move closer if needed.",
    )
    add(
        "lighting",
        sum(s["lighting"] for s in single) / count >= 0.85,
        "Use even lighting in front of your face. Avoid darkness, glare and strong backlighting.",
    )
    add(
        "sharpness",
        sum(s["sharp"] for s in single) / count >= 0.85,
        "Clean the lens, hold the phone steady and wait for the camera to focus.",
    )

    def neutral(s):
        return s["blink"] < 0.3 and s["jaw"] < 0.2 and abs(s["turn"] - 0.5) < 0.16

    baseline = [s for s in usable if s["t"] < BASELINE_SECONDS and neutral(s)]
    add(
        "neutral_start",
        len(baseline) >= 5,
        "Start facing forward with eyes open and your mouth relaxed.",
    )
    for index, action in enumerate(actions):
        start = BASELINE_SECONDS + index * ACTION_SECONDS
        window = [s for s in usable if start <= s["t"] < start + ACTION_SECONDS]
        state = 0
        active_count = 0
        for sample in window:
            active = {
                "blink": sample["blink"] > 0.55,
                "open_mouth": sample["jaw"] > 0.4,
                "turn_head": abs(sample["turn"] - 0.5) > 0.22,
            }[action]
            if state == 0 and neutral(sample):
                state = 1
            elif state == 1:
                active_count = active_count + 1 if active else 0
                if active_count >= 2:
                    state = 2
            elif state == 2 and neutral(sample):
                state = 3
        add(action, state == 3, f"Follow the prompt: {LABELS[action].lower()}.")
    passed = all(c["passed"] for c in checks)
    return {
        "version": "guided-v1",
        "passed": passed,
        "status": "guided_checks_passed" if passed else "retake_required",
        "liveness": "not_verified",
        "manual_review_required": True,
        "checks": checks,
    }


def assess_video(path, actions, settings):
    if not _slot.acquire(blocking=False):
        raise HTTPException(503, "Video checks are busy. Keep your preview and retry shortly.")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "app.processes.face_worker",
                str(path),
                settings.face_model_path,
                settings.ffmpeg_path,
                json.dumps(actions),
            ],
            capture_output=True,
            timeout=90,
            check=True,
        )
        report = json.loads(result.stdout)
        if (
            not isinstance(report, dict)
            or not isinstance(report.get("passed"), bool)
            or not report.get("checks")
        ):
            raise ValueError("Invalid assessment output")
        return report
    except (OSError, subprocess.SubprocessError, ValueError):
        raise HTTPException(
            503,
            "Video checks are unavailable. Keep your preview and retry, or contact your operator.",
        ) from None
    finally:
        _slot.release()
