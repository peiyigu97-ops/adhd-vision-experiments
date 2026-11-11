"""
GC0308 - offline re-run of the median-filter detector variant on the
ALREADY-CAPTURED cropped samples (gc0308_pupil_test_cropped.py's output).
No new camera session needed -- this answers "does denoising help" using
the same 61 images already on disk, so no additional IR/camera exposure
is required from the user.
"""
import cv2
import os
import csv
from pupil_detector_denoised import detect_pupil

BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(BASE, "data", "gc0308_samples_cropped")
PROCESSED_DIR = os.path.join(BASE, "data", "gc0308_processed_denoised")
RESULTS_DIR = os.path.join(BASE, "data", "gc0308_results")
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def main():
    files = sorted(f for f in os.listdir(SAMPLES_DIR) if f.endswith(".png"))
    if not files:
        print(f"No images found in {SAMPLES_DIR}")
        return

    rows = []
    success_count = 0
    for fname in files:
        gray = cv2.imread(os.path.join(SAMPLES_DIR, fname), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        pres = detect_pupil(gray)
        vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        if pres["success"]:
            success_count += 1
            cv2.ellipse(vis, pres["ellipse"], (0, 255, 0), 1)
            cv2.drawContours(vis, [pres["contour"]], -1, (255, 0, 0), 1)
            cx, cy = int(pres["pupil_cx"]), int(pres["pupil_cy"])
            cv2.circle(vis, (cx, cy), 2, (0, 0, 255), -1)
            print(f"  {fname}: SUCCESS confidence={pres['confidence']}")
        else:
            cv2.putText(vis, "FAIL", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            print(f"  {fname}: FAILED -- {pres['reason']}")
        cv2.imwrite(os.path.join(PROCESSED_DIR, f"annotated_{fname}"), vis)
        rows.append({
            "filename": fname, "success": pres["success"], "reason": pres["reason"],
            "pupil_x": pres["pupil_cx"], "pupil_y": pres["pupil_cy"], "confidence": pres["confidence"],
        })

    csv_path = os.path.join(RESULTS_DIR, "gc0308_pupil_detection_denoised.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "success", "reason", "pupil_x", "pupil_y", "confidence"])
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    print(f"\n--- Summary (median-filter denoised, same 61 cropped images) ---")
    print(f"  Total: {total}, Success (raw, before visual audit): {success_count} "
          f"({100.0*success_count/total:.1f}%)" if total else "  No samples.")
    print(f"  Compare: same images without denoising -> 0/61 real success (2 raw 'successes' were false positives on visual audit)")
    print(f"  CSV: {csv_path}")
    print(f"  Annotated images: {PROCESSED_DIR}")

if __name__ == "__main__":
    main()
