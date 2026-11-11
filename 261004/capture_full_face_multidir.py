"""
Full-face, multi-direction capture with a live preview window, for MediaPipe
FaceLandmarker (iris landmark) testing under 261010 roadmap section 6.3 (Plan B).

Extends capture_full_face.py: that script only captured ~4s of frames while
looking straight at the camera (19 frames, mostly center-ish gaze), which
under-covers gaze direction. This script adds:
  - a live preview window (viewfinder) so you can see yourself and frame
    your face before each direction segment
  - an on-screen + console prompt cycling through several gaze directions
    (center / left / right / up / down), so the sample covers more of the
    gaze range instead of just center

Still non-interactive -- no keypress needed, just look where it says to.
Saved frames go to a NEW directory (face_full_multidir/) so the original
19-frame batch in data/face_full/ (already analyzed, numbers already written
into the roadmap doc) is not overwritten.

No IR illuminator used here (matches the no-IR condition elsewhere in
261004/data).

Usage:
    python capture_full_face_multidir.py
Output:
    data/face_full_multidir/face_<direction>_<index>.png
"""
import cv2
import numpy as np
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
FACE_DIR = os.path.join(DATA_DIR, "face_full_multidir")
os.makedirs(FACE_DIR, exist_ok=True)

# Same camera config as eye_roi.py / capture_raw.py / capture_full_face.py,
# re-verified 2026-10-08: index 0 = OV9281. Rerun identify_camera.py first if
# captures look wrong (unexpectedly colored, or dark) -- do not assume this
# mapping is still correct without checking if something looks off.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720

# (direction label, on-screen prompt text, prep seconds, capture seconds)
DIRECTIONS = [
    ("center", "look at CENTER / dot", 1.5, 2.0),
    ("left",   "look LEFT",            1.5, 2.0),
    ("right",  "look RIGHT",           1.5, 2.0),
    ("up",     "look UP",              1.5, 2.0),
    ("down",   "look DOWN",            1.5, 2.0),
    ("center", "look at CENTER again", 1.5, 2.0),
]
FRAME_INTERVAL = 0.2  # seconds between saved frames during a capture segment


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


def show(window, frame_bgr, big_text, sub_text="", color=(0, 255, 0)):
    """Draw a viewfinder frame with large centered prompt text, then pump
    the GUI event loop. waitKey(1) is only used to flush the window's event
    queue -- no keypress is required or waited on."""
    disp = frame_bgr.copy()
    h, w = disp.shape[:2]
    if big_text:
        cv2.putText(disp, big_text, (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.6,
                    color, 4, cv2.LINE_AA)
    if sub_text:
        cv2.putText(disp, sub_text, (40, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imshow(window, disp)
    cv2.waitKey(1)


def main():
    cap = open_camera()
    window = "Full-face capture (viewfinder) - no action needed, just look"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    # warm up (first frames from UVC cameras can be dark/uninitialized)
    for _ in range(10):
        ret, frame = cap.read()
        if ret:
            show(window, frame, "")

    print("Full-face multi-direction capture for MediaPipe FaceLandmarker test (no IR).")
    print("A preview window has opened. Keep your face centered in frame.")
    for n in (3, 2, 1):
        ret, frame = cap.read()
        if ret:
            show(window, frame, f"Starting in {n}...", "Get ready, face centered")
        print(f"  {n}...")
        time.sleep(1.0)

    saved_counts = {}
    total_saved = 0
    for direction, prompt, prep_s, cap_s in DIRECTIONS:
        idx = saved_counts.get(direction, 0)

        # Prep phase: show the prompt, don't save yet, give time to turn gaze.
        prep_start = time.time()
        while time.time() - prep_start < prep_s:
            ret, frame = cap.read()
            if not ret:
                continue
            show(window, frame, prompt, "get ready...", color=(0, 200, 255))
        print(f"-> {prompt}")

        # Capture phase: save frames at a fixed interval.
        cap_start = time.time()
        last_save = 0.0
        while time.time() - cap_start < cap_s:
            ret, frame = cap.read()
            if not ret:
                continue
            now = time.time()
            show(window, frame, prompt, "capturing...", color=(0, 255, 0))
            if now - last_save >= FRAME_INTERVAL:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                path = os.path.join(FACE_DIR, f"face_{direction}_{idx:02d}.png")
                if imwrite_unicode(path, gray):
                    idx += 1
                    total_saved += 1
                last_save = now

        saved_counts[direction] = idx

    cap.release()
    cv2.destroyAllWindows()

    print(f"\nSaved {total_saved} full-face frames to {FACE_DIR}")
    for direction, count in saved_counts.items():
        print(f"  {direction}: {count} frames (cumulative if direction repeated)")


if __name__ == "__main__":
    main()
