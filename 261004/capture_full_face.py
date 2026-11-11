"""
Non-interactive full-face capture, for MediaPipe FaceLandmarker (iris landmark)
testing under 261010 roadmap section 6.3 (Plan B).

Why this exists: data/eye/*.png are already eye-only crops (see eye_roi.py --
the Haar cascade crops the eye region in-memory and only the crop is ever
saved; the full-face frame is discarded immediately after detection). MediaPipe
FaceLandmarker's face detector needs the whole face (both eyes, nose, mouth)
to align landmarks -- feeding it an eye-only crop would fail at the face
detection stage, which would misleadingly look like "iris landmarks don't
work" when actually the input was wrong. This script captures real full-face
frames so that question can be tested properly.

No IR illuminator used here (matches the no-IR condition in 261004/data/eye,
so any result is comparable to the existing Otsu/starburst no-IR baseline).

Usage:
    python capture_full_face.py
Behavior:
    3-second countdown (printed to console), then captures a short burst of
    full-face frames over ~4 seconds. No GUI window, no keypress needed --
    just look at the camera when the countdown says so.
Output:
    data/face_full/face_<index>.png  (grayscale, same convention as capture_raw.py)
"""
import cv2
import numpy as np
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
FACE_DIR = os.path.join(DATA_DIR, "face_full")
os.makedirs(FACE_DIR, exist_ok=True)

# Same camera config as eye_roi.py / capture_raw.py, re-verified 2026-10-08:
# index 0 = OV9281. Rerun identify_camera.py first if captures look wrong
# (unexpectedly colored, or dark) -- do not assume this mapping is still
# correct without checking if something looks off.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720

CAPTURE_SECONDS = 4.0


def imwrite_unicode(path, img):
    """cv2.imwrite fails silently on non-ASCII (CJK) Windows paths; this
    project tree lives under 作品集/课程/..., so always write through
    cv2.imencode + ndarray.tofile instead (established in compare_algorithms.py)."""
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera index {CAMERA_INDEX}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    return cap


def main():
    cap = open_camera()

    # warm up (first frames from UVC cameras can be dark/uninitialized)
    for _ in range(10):
        cap.read()

    print("Full-face capture for MediaPipe FaceLandmarker test (no IR).")
    print("Look directly at the camera, face centered, normal room lighting.")
    for n in (3, 2, 1):
        print(f"  {n}...")
        time.sleep(1.0)
    print("Capturing now -- hold still, small movement is fine.")

    saved = 0
    start = time.time()
    while time.time() - start < CAPTURE_SECONDS:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        path = os.path.join(FACE_DIR, f"face_{saved:02d}.png")
        if imwrite_unicode(path, gray):
            saved += 1
        time.sleep(0.2)

    cap.release()
    elapsed = time.time() - start
    print(f"\nSaved {saved} full-face frames to {FACE_DIR} ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
