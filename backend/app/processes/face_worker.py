"""Isolated, time-limited video decoding and MediaPipe inference; no network calls."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from app.processes.assessment import RECORDING_SECONDS, evaluate_samples


def frame_sample(frame, result, timestamp):
    sample = {"t": timestamp, "faces": len(result.face_landmarks)}
    if sample["faces"] != 1:
        return sample
    points = result.face_landmarks[0]
    x = [p.x for p in points]
    y = [p.y for p in points]
    left, right, top, bottom = min(x), max(x), min(y), max(y)
    height, width = frame.shape[:2]
    sample["framed"] = (
        left >= 0.025
        and right <= 0.975
        and top >= 0.025
        and bottom <= 0.975
        and (right - left) * width >= 96
        and (bottom - top) * height >= 110
        and right - left <= 0.85
        and bottom - top <= 0.9
    )
    roi = frame[
        max(0, int(top * height)) : min(height, int(bottom * height)),
        max(0, int(left * width)) : min(width, int(right * width)),
    ]
    sample.update(lighting=False, sharp=False, blink=0.0, jaw=0.0, turn=0.5)
    if roi.size:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Exposure is measured on the face, not inferred from the background.
        mean = float(np.mean(gray))
        sample["lighting"] = (
            45 <= mean <= 215
            and float(np.mean(gray < 25)) < 0.45
            and float(np.mean(gray > 240)) < 0.35
        )
        sample["sharp"] = float(cv2.Laplacian(gray, cv2.CV_64F).var()) >= 25
    blends = {c.category_name: c.score for c in result.face_blendshapes[0]}
    sample["blink"] = min(blends.get("eyeBlinkLeft", 0), blends.get("eyeBlinkRight", 0))
    sample["jaw"] = blends.get("jawOpen", 0)
    # Nose relative to cheek landmarks, independent of translation and image scale.
    cheek_left, cheek_right = sorted([points[234].x, points[454].x])
    sample["turn"] = (points[1].x - cheek_left) / max(cheek_right - cheek_left, 0.001)
    return sample


def main():
    path, model, ffmpeg, actions = sys.argv[1:]
    cv2.setNumThreads(1)
    # Parent upload cleanup also removes frames if this worker is killed on timeout.
    with tempfile.TemporaryDirectory(prefix="visa-face-", dir=Path(path).parent) as temp:
        subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-threads",
                "1",
                "-protocol_whitelist",
                "file,pipe",
                "-i",
                path,
                "-an",
                "-t",
                str(RECORDING_SECONDS + 1),
                "-vf",
                "fps=10,scale=480:480:force_original_aspect_ratio=decrease",
                "-threads",
                "1",
                "-frames:v",
                "190",
                str(Path(temp) / "%04d.png"),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_faces=2,
            min_face_detection_confidence=0.6,
            min_face_presence_confidence=0.6,
            output_face_blendshapes=True,
        )
        samples = []
        with mp.tasks.vision.FaceLandmarker.create_from_options(options) as detector:
            for index, file in enumerate(sorted(Path(temp).glob("*.png"))):
                frame = cv2.imread(str(file))
                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                )
                result = detector.detect_for_video(image, index * 100)
                samples.append(frame_sample(frame, result, index / 10))
        print(json.dumps(evaluate_samples(samples, json.loads(actions))))


if __name__ == "__main__":
    main()
