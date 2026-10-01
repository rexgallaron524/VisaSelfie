"""Fetch the pinned Google MediaPipe model at build time, never during a request."""

import hashlib
import urllib.request
from pathlib import Path

URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"


def main():
    target = Path(__file__).parent / "models" / "face_landmarker.task"
    data = urllib.request.urlopen(URL, timeout=60).read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError("Face model checksum mismatch")
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(data)
    print("Verified face model installed")


if __name__ == "__main__":
    main()
