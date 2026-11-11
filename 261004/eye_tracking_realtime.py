"""
STEP 7 + STEP 8: Real-time pupil visualization + gaze_raw.csv logging.

Displays:
  - Original frame with eye ROI rectangle
  - Eye ROI window with pupil contour + ellipse + center marker overlaid
    when detection succeeds
  - On-screen text: timestamp, pupil_x, pupil_y, confidence (per project
    requirement -- not just drawn silently)

Logs every frame to data/results/gaze_raw.csv with columns:
  timestamp, frame, roi_found, pupil_x, pupil_y, pupil_width, pupil_height, confidence
When detection fails: pupil_x/pupil_y = NaN, confidence = 0 (never faked).
roi_found separates "Haar cascade couldn't locate an eye region at all" from
"eye region found but pupil detection itself failed" -- added 2026-10-09
after a first live session (13063 frames, 3.39% pupil hit rate) couldn't be
compared against Stage 6c's 27.2% (fair-frame) static-sample number, because
the two failure modes were conflated into one NaN bucket. This field lets
the two rates be computed separately: eye-ROI hit rate (comparable to Stage
5's 15.5%) and pupil-detection-given-ROI rate (comparable to Stage 6c's
27.2%).

Also writes data/results/metadata.json with camera resolution and measured FPS
for this session (measured the same way as Stage 4: frames / elapsed_time,
not CAP_PROP_FPS).

Controls: 'q' to quit.

KNOWN LIMITATION (carried over from Stage 6 findings): under current hardware
(no IR illumination, no IR-cut filter), the pupil detector's validated success
rate on static samples was 0/20. Running this live is expected to produce a
gaze_raw.csv that is mostly NaN rows. This script still writes that data
truthfully -- the goal here is to validate the acquisition -> detection ->
logging pipeline end-to-end, not to claim working pupil tracking.
"""
import cv2
import time
import csv
import json
import os
from pupil_detector import detect_eye, detect_pupil

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE, "data", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Re-verified 2026-10-08 via identify_camera.py: index mapping had flipped
# (was 1=OV9281 on 2026-10-04, now 0=OV9281) after a USB re-enumeration event.
# If captures look wrong (unexpectedly dark, or colored instead of monochrome),
# rerun identify_camera.py to reconfirm before assuming the IR LED is broken.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720
CSV_PATH = os.path.join(RESULTS_DIR, "gaze_raw.csv")
METADATA_PATH = os.path.join(RESULTS_DIR, "metadata.json")


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print("Controls: 'q' to quit")
    print(f"Logging to {CSV_PATH}")

    csv_file = open(CSV_PATH, "w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow(["timestamp", "frame", "roi_found", "pupil_x", "pupil_y",
                      "pupil_width", "pupil_height", "confidence"])

    frame_idx = 0
    session_start = time.time()
    roi_hits = 0
    detect_hits = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        frame_idx += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ts = time.time()

        roi = detect_eye(gray)
        display = frame.copy()

        roi_found = roi is not None
        pupil_x, pupil_y, pupil_w, pupil_h, conf = float("nan"), float("nan"), float("nan"), float("nan"), 0.0

        if roi is not None:
            roi_hits += 1
            x, y, w, h = roi
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            eye_gray = gray[y:y + h, x:x + w]
            pres = detect_pupil(eye_gray)

            eye_vis = cv2.cvtColor(eye_gray, cv2.COLOR_GRAY2BGR)
            if pres["success"]:
                detect_hits += 1
                cv2.ellipse(eye_vis, pres["ellipse"], (0, 255, 0), 1)
                cv2.drawContours(eye_vis, [pres["contour"]], -1, (255, 0, 0), 1)
                cx, cy = int(pres["pupil_cx"]), int(pres["pupil_cy"])
                cv2.circle(eye_vis, (cx, cy), 2, (0, 0, 255), -1)
                pupil_x, pupil_y = pres["pupil_cx"], pres["pupil_cy"]
                pupil_w, pupil_h = pres["pupil_w"], pres["pupil_h"]
                conf = pres["confidence"]
            cv2.imshow("Eye ROI", eye_vis)

        writer.writerow([f"{ts:.3f}", frame_idx, roi_found, pupil_x, pupil_y, pupil_w, pupil_h, conf])

        roi_rate = 100.0 * roi_hits / frame_idx
        pupil_given_roi_rate = 100.0 * detect_hits / roi_hits if roi_hits > 0 else 0.0
        cv2.putText(display, f"t={ts:.2f} x={pupil_x} y={pupil_y} conf={conf}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.putText(display, f"ROI hit: {roi_rate:.1f}% | Pupil|ROI: {pupil_given_roi_rate:.1f}% ({detect_hits}/{roi_hits})",
                    (20, HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.imshow("Original frame", display)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    elapsed = time.time() - session_start
    measured_fps = frame_idx / elapsed if elapsed > 0 else 0

    cap.release()
    cv2.destroyAllWindows()
    csv_file.close()

    metadata = {
        "camera_index": CAMERA_INDEX,
        "resolution_requested": f"{WIDTH}x{HEIGHT}",
        "resolution_actual": f"{actual_w}x{actual_h}",
        "session_duration_seconds": round(elapsed, 2),
        "total_frames": frame_idx,
        "measured_fps": round(measured_fps, 2),
        "roi_hits": roi_hits,
        "roi_hit_rate_pct": round(100.0 * roi_hits / frame_idx, 2) if frame_idx else 0,
        "pupil_detect_hits": detect_hits,
        "pupil_detect_rate_pct_of_all_frames": round(100.0 * detect_hits / frame_idx, 2) if frame_idx else 0,
        "pupil_detect_rate_pct_given_roi": round(100.0 * detect_hits / roi_hits, 2) if roi_hits else 0,
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nSession summary:")
    print(f"  Total frames: {frame_idx}")
    print(f"  Measured FPS (this session, with detection+display overhead): {measured_fps:.2f}")
    print(f"  Eye-ROI hit rate (Haar cascade, comparable to Stage 5's 15.5%): {metadata['roi_hit_rate_pct']}%")
    print(f"  Pupil detect rate of ALL frames: {metadata['pupil_detect_rate_pct_of_all_frames']}%")
    print(f"  Pupil detect rate GIVEN a found ROI (comparable to Stage 6c's 27.2%): "
          f"{metadata['pupil_detect_rate_pct_given_roi']}%")
    print(f"  gaze_raw.csv saved to {CSV_PATH}")
    print(f"  metadata.json saved to {METADATA_PATH}")

if __name__ == "__main__":
    main()
