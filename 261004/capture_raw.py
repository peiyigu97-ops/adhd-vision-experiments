"""
STEP 5: Capture raw frames from OV9281 (index=1, DSHOW, 1280x720).

Saves:
- 10 static grayscale frames to data/raw/
- a 5-second continuous PNG sequence to data/raw/sequence/
  (PNG chosen over lossy JPEG per project requirement -- no compression artifacts
  for later pupil-detection analysis)

OV9281 already outputs monochrome content but OpenCV/DSHOW reports it as a
3-channel BGR frame (all channels equal). We convert to true single-channel
grayscale before saving so downstream analysis works on real 8-bit intensity
data, not a replicated 3-channel image.
"""
import cv2
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
SEQ_DIR = os.path.join(RAW_DIR, "sequence")
EYE_DIR = os.path.join(DATA_DIR, "eye")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

for d in [RAW_DIR, SEQ_DIR, EYE_DIR, PROCESSED_DIR, RESULTS_DIR]:
    os.makedirs(d, exist_ok=True)

# Re-verified 2026-10-08 via identify_camera.py: index mapping had flipped
# (was 1=OV9281 on 2026-10-04, now 0=OV9281) after a USB re-enumeration event.
# If captures look wrong (unexpectedly dark, or colored instead of monochrome),
# rerun identify_camera.py to reconfirm before assuming the IR LED is broken.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720

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

    print("Capturing 10 static grayscale frames...")
    saved = 0
    attempts = 0
    while saved < 10 and attempts < 30:
        ret, frame = cap.read()
        attempts += 1
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        path = os.path.join(RAW_DIR, f"frame_{saved:02d}.png")
        cv2.imwrite(path, gray)
        saved += 1
        time.sleep(0.2)
    print(f"  Saved {saved} static frames to {RAW_DIR}")

    print("\nCapturing 5-second continuous PNG sequence...")
    frame_count = 0
    start = time.time()
    while time.time() - start < 5.0:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        path = os.path.join(SEQ_DIR, f"seq_{frame_count:05d}.png")
        cv2.imwrite(path, gray)
        frame_count += 1
    elapsed = time.time() - start
    cap.release()

    print(f"  Saved {frame_count} sequence frames to {SEQ_DIR}")
    print(f"  Elapsed: {elapsed:.2f}s, effective FPS during save: {frame_count/elapsed:.2f}")
    print("\nNote: FPS during PNG-writing capture may be lower than the raw")
    print("117 FPS measured earlier, since disk write time is now included")
    print("in the loop. This is expected and will be reported, not hidden.")

if __name__ == "__main__":
    main()
