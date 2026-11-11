"""
GC0308 module - Step 3+4: image quality analysis + pupil detection test.

Combines what was Stage 4 (image quality stats) and Stage 6c (pupil
detection) for the OV9281 line, applied to the GC0308 module instead.
This module has its own IR LED built in (per product listing), so unlike
the OV9281 "no IR" baseline, this is inherently an IR-illuminated test from
the start.

Captures N eye ROI samples by letting the user manually position the module
close to the eye (no Haar cascade auto-ROI here -- at ~1280x... actually at
this module's close-up working distance, the eye should already fill most
of the frame, so we treat the WHOLE FRAME as the ROI, no face/eye detection
needed). Runs the identical pupil_detector logic (same Otsu+contour+ellipse
pipeline, same circularity threshold 0.75) used for OV9281, so results are
directly comparable apples-to-apples.

Controls: 's' save current frame + run detection, 'q' quit.
"""
import cv2
import os
import csv
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pupil_detector_base import detect_pupil  # same algorithm as OV9281 tests

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(BASE, "data", "gc0308_samples")
PROCESSED_DIR = os.path.join(BASE, "data", "gc0308_processed")
RESULTS_DIR = os.path.join(BASE, "data", "gc0308_results")
for d in [SAMPLES_DIR, PROCESSED_DIR, RESULTS_DIR]:
    os.makedirs(d, exist_ok=True)

CAMERA_INDEX = 1  # confirmed via identify_gc0308.py
WIDTH, HEIGHT = 640, 480  # confirmed as the module's working resolution via gc0308_fps_test.py


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    print("Position the module close to your eye (its native working distance,")
    print("a few cm) so the eye fills most of the frame -- same as the")
    print("identify_gc0308.py close-up sample.")
    print("\nControls: 's' save + run pupil detection | 'q' quit")

    saved = 0
    rows = []

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        display = frame.copy()
        cv2.putText(display, f"Saved: {saved}", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.imshow("GC0308 - press s to save+detect, q to quit", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            fname = f"gc0308_{int(time.time()*1000)}.png"
            cv2.imwrite(os.path.join(SAMPLES_DIR, fname), gray)

            # Whole frame is the "ROI" here since the module is used close-up
            # and the eye already fills the frame -- no face/eye cascade needed.
            pres = detect_pupil(gray)
            vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            if pres["success"]:
                cv2.ellipse(vis, pres["ellipse"], (0, 255, 0), 1)
                cv2.drawContours(vis, [pres["contour"]], -1, (255, 0, 0), 1)
                cx, cy = int(pres["pupil_cx"]), int(pres["pupil_cy"])
                cv2.circle(vis, (cx, cy), 2, (0, 0, 255), -1)
                print(f"  [{fname}] SUCCESS center=({pres['pupil_cx']},{pres['pupil_cy']}) "
                      f"confidence={pres['confidence']}")
            else:
                cv2.putText(vis, "FAIL", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                print(f"  [{fname}] FAILED -- {pres['reason']}")

            cv2.imwrite(os.path.join(PROCESSED_DIR, f"annotated_{fname}"), vis)
            rows.append({
                "filename": fname,
                "success": pres["success"],
                "reason": pres["reason"],
                "pupil_x": pres["pupil_cx"],
                "pupil_y": pres["pupil_cy"],
                "confidence": pres["confidence"],
            })
            saved += 1

    cap.release()
    cv2.destroyAllWindows()

    csv_path = os.path.join(RESULTS_DIR, "gc0308_pupil_detection.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "success", "reason", "pupil_x", "pupil_y", "confidence"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    total = len(rows)
    success_count = sum(1 for r in rows if r["success"])
    print(f"\n--- Summary (GC0308, built-in IR) ---")
    print(f"  Total samples: {total}")
    if total:
        print(f"  Successful pupil detections (raw, before visual fair-frame audit): "
              f"{success_count} ({100.0*success_count/total:.1f}%)")
    print(f"  Compare to OV9281 baselines: no-IR 0/20 (0%), IR+external LED 22/81 (27.2%, fair frames)")
    print(f"  CSV saved to {csv_path}")
    print(f"  Annotated images saved to {PROCESSED_DIR}")
    print(f"  Raw samples saved to {SAMPLES_DIR}")

if __name__ == "__main__":
    main()
