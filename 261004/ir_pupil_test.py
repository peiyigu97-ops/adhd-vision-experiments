"""
STEP 6c: Combined IR-ON capture + pupil detection test.

After two inconclusive brightness-comparison attempts (ir_comparison.py) --
one invalidated by head movement, one confounded by manual exposure locking
behaving unreliably on this camera/driver -- this script drops the
brightness-metric approach entirely. Auto-exposure is left ON (normal
operating condition), and the question is answered directly and only by the
metric that actually matters: does pupil_detector.py succeed more often on
IR-illuminated ROI crops than it did in Stage 6 (0/20, no IR)?

Flow:
  1. Auto-detect eye ROI (Haar cascade, same as Stage 5) while the IR LED is ON.
  2. Save each ROI crop to data/eye_ir/.
  3. Immediately run the same pupil_detector.detect_pupil() used in Stage 6
     on every saved crop.
  4. Report success count/rate and save annotated images, directly comparable
     to Stage 6's pupil_detection.csv (0/20 baseline, no IR).

Controls: 's' save + detect on current ROI, 'q' quit after collecting enough
samples (aim for ~15-20, same order as Stage 6 for a fair comparison).
"""
import cv2
import os
import csv
import time
from pupil_detector import detect_eye, detect_pupil

BASE = os.path.dirname(os.path.abspath(__file__))
EYE_IR_DIR = os.path.join(BASE, "data", "eye_ir")
PROCESSED_DIR = os.path.join(BASE, "data", "processed", "pupil_ir")
RESULTS_DIR = os.path.join(BASE, "data", "results")
for d in [EYE_IR_DIR, PROCESSED_DIR, RESULTS_DIR]:
    os.makedirs(d, exist_ok=True)

# Re-verified 2026-10-08 via identify_camera.py: index mapping had flipped
# (was 1=OV9281 on 2026-10-04, now 0=OV9281) after a USB re-enumeration event.
# If captures look wrong (unexpectedly dark, or colored instead of monochrome),
# rerun identify_camera.py to reconfirm before assuming the IR LED is broken.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    print("Make sure the IR LED is ON and pointed at your eye (not at the lens).")
    print("Auto-exposure is left ON -- this test only measures pupil detection")
    print("success rate, not raw brightness.")
    print("\nControls: 's' save ROI + run detection | 'q' quit")

    saved = 0
    rows = []

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        display = frame.copy()

        roi = detect_eye(gray)
        if roi is not None:
            x, y, w, h = roi
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
        else:
            cv2.putText(display, "No eye ROI detected", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cv2.putText(display, f"Saved: {saved}", (20, HEIGHT - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.imshow("IR capture - press s to save, q to quit", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            if roi is None:
                print("  No ROI detected right now, try repositioning.")
                continue
            x, y, w, h = roi
            eye_gray = gray[y:y + h, x:x + w]
            fname = f"eye_ir_{int(time.time()*1000)}.png"
            cv2.imwrite(os.path.join(EYE_IR_DIR, fname), eye_gray)

            pres = detect_pupil(eye_gray)
            vis = cv2.cvtColor(eye_gray, cv2.COLOR_GRAY2BGR)
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

    csv_path = os.path.join(RESULTS_DIR, "pupil_detection_ir.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "success", "reason", "pupil_x", "pupil_y", "confidence"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    total = len(rows)
    success_count = sum(1 for r in rows if r["success"])
    print(f"\n--- Summary (IR ON) ---")
    print(f"  Total samples: {total}")
    print(f"  Successful pupil detections: {success_count} ({100.0*success_count/total:.1f}%)" if total else "  No samples collected.")
    print(f"  Compare to Stage 6 baseline (no IR): 0/20 (0.0%)")
    print(f"  CSV saved to {csv_path}")
    print(f"  Annotated images saved to {PROCESSED_DIR}")

if __name__ == "__main__":
    main()
