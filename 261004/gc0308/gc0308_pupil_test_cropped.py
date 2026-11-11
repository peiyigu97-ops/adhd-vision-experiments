"""
GC0308 module - Step 3b: pupil detection with manual ROI crop (excludes nose-bridge noise).

Root cause found in the first full-frame test (gc0308_pupil_test.py, 73/73 fail):
visually inspecting the raw samples showed the eye/iris/pupil region itself
was actually reasonably sharp, but a large patch of sensor noise (speckled
granular texture, likely high-gain noise from this cheap 0.3MP sensor under
the module's close-up lighting) appears over the nose-bridge/under-eye skin
area in most frames. That noise patch is large and irregular enough to get
picked up by the contour/area filter and compete with the real pupil contour
for "best circularity", and also fragments the dark-pupil blob at the Otsu
threshold stage.

Fix tried here: let the user manually select a tight ROI around just the
eye (cv2.selectROI, same mechanism as eye_roi.py's Plan A fallback for
OV9281) ONCE at the start of the session, excluding the nose-bridge area.
Since this module is used at a fixed close-up working distance, one manual
crop should remain valid for consecutive captures without needing per-frame
re-selection -- if the module moves significantly, re-run this script.

Uses the identical pupil_detector algorithm/threshold as OV9281 tests (no
parameter changes), so a fair comparison is still possible: this isolates
"did restricting the ROI fix it" as the only variable.
"""
import cv2
import os
import csv
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pupil_detector_base import detect_pupil

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(BASE, "data", "gc0308_samples_cropped")
PROCESSED_DIR = os.path.join(BASE, "data", "gc0308_processed_cropped")
RESULTS_DIR = os.path.join(BASE, "data", "gc0308_results")
for d in [SAMPLES_DIR, PROCESSED_DIR, RESULTS_DIR]:
    os.makedirs(d, exist_ok=True)

CAMERA_INDEX = 1
WIDTH, HEIGHT = 640, 480


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    for _ in range(10):
        cap.read()

    print("Position the module at your eye as before.")
    print("A window will open -- drag a TIGHT box around just the eye")
    print("(exclude nose bridge / under-eye skin where the noise patch appears).")
    print("Press ENTER/SPACE to confirm the crop, 'c' to cancel.")

    ret, frame = cap.read()
    if not ret:
        print("Failed to read initial frame.")
        return
    roi = cv2.selectROI("Select eye region (exclude nose bridge)", frame, showCrosshair=True)
    cv2.destroyWindow("Select eye region (exclude nose bridge)")
    rx, ry, rw, rh = roi
    if rw == 0 or rh == 0:
        print("No ROI selected, exiting.")
        return
    print(f"Using fixed crop: x={rx}, y={ry}, w={rw}, h={rh}")
    print("\nControls: 's' save + run detection on this crop | 'q' quit")

    saved = 0
    rows = []

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        crop = gray_full[ry:ry + rh, rx:rx + rw]

        display = frame.copy()
        cv2.rectangle(display, (rx, ry), (rx + rw, ry + rh), (0, 255, 0), 1)
        cv2.putText(display, f"Saved: {saved}", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.imshow("GC0308 cropped - s=save+detect, q=quit", display)
        cv2.imshow("Cropped ROI", crop)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            fname = f"gc0308_crop_{int(time.time()*1000)}.png"
            cv2.imwrite(os.path.join(SAMPLES_DIR, fname), crop)

            pres = detect_pupil(crop)
            vis = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
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

    csv_path = os.path.join(RESULTS_DIR, "gc0308_pupil_detection_cropped.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "success", "reason", "pupil_x", "pupil_y", "confidence"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    total = len(rows)
    success_count = sum(1 for r in rows if r["success"])
    print(f"\n--- Summary (GC0308, manual eye-only crop, excludes nose-bridge noise) ---")
    print(f"  Total samples: {total}")
    if total:
        print(f"  Successful pupil detections (raw, before visual fair-frame audit): "
              f"{success_count} ({100.0*success_count/total:.1f}%)")
    print(f"  Compare to: GC0308 full-frame 0/73 (0%); OV9281 no-IR 0/20 (0%); "
          f"OV9281 IR+external LED 22/81 (27.2%, fair frames)")
    print(f"  CSV saved to {csv_path}")

if __name__ == "__main__":
    main()
