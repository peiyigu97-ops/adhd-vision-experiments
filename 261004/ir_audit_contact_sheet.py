"""
STEP 6c-audit: Visual quality audit of the 100 IR-ON eye ROI samples.

The raw success rate computed by pupil_detector.py (22/100 = 22%) conflates
two very different kinds of "failure":
  (a) the eye was genuinely open, in focus, reasonably exposed -- a fair
      test of the detector -- but the classical threshold/contour/ellipse
      pipeline still failed to find the pupil.
  (b) the frame itself was not a fair test at all: eye closed/blinking,
      severe motion blur, or massive over/under-exposure that makes pupil
      detection impossible in principle, regardless of algorithm quality.

Counting (b) frames in the denominator understates the detector's real
capability on usable frames, and overstates it if (b) frames coincidentally
"succeed" by accident. This script does NOT guess the open/closed/blur
classification algorithmically (that would just be swapping one unverified
heuristic for another) -- it builds a labeled contact sheet so each of the
100 frames can be visually inspected and classified by hand, then
cross-tabulates classification x detector outcome into an honest table.

Output: data/results/ir_audit_contact_sheets/sheet_00.png ... sheet_03.png
(25 thumbnails each, labeled with index + detector success/fail), and a
data/results/ir_audit_template.csv to fill in the visual classification.
"""
import cv2
import os
import csv
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
EYE_IR_DIR = os.path.join(BASE, "data", "eye_ir")
RESULTS_DIR = os.path.join(BASE, "data", "results")
AUDIT_DIR = os.path.join(RESULTS_DIR, "ir_audit_contact_sheets")
os.makedirs(AUDIT_DIR, exist_ok=True)

CSV_PATH = os.path.join(RESULTS_DIR, "pupil_detection_ir.csv")
TEMPLATE_PATH = os.path.join(RESULTS_DIR, "ir_audit_template.csv")

THUMB = 140
COLS, ROWS = 5, 5
PER_SHEET = COLS * ROWS


def main():
    with open(CSV_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    n = len(rows)
    n_sheets = (n + PER_SHEET - 1) // PER_SHEET

    template_rows = []

    for sheet_idx in range(n_sheets):
        canvas = np.full((ROWS * (THUMB + 30), COLS * THUMB, 3), 255, dtype=np.uint8)
        batch = rows[sheet_idx * PER_SHEET:(sheet_idx + 1) * PER_SHEET]

        for i, row in enumerate(batch):
            global_idx = sheet_idx * PER_SHEET + i
            r, c = divmod(i, COLS)
            img_path = os.path.join(EYE_IR_DIR, row["filename"])
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            thumb = cv2.resize(img, (THUMB, THUMB))
            thumb_bgr = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR)

            y0 = r * (THUMB + 30)
            x0 = c * THUMB
            canvas[y0:y0 + THUMB, x0:x0 + THUMB] = thumb_bgr

            success = row["success"] == "True"
            color = (0, 150, 0) if success else (0, 0, 200)
            label = f"#{global_idx} {'OK' if success else 'FAIL'}"
            cv2.putText(canvas, label, (x0 + 2, y0 + THUMB + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

            template_rows.append({
                "global_index": global_idx,
                "filename": row["filename"],
                "detector_success": row["success"],
                "confidence": row["confidence"],
                "visual_eye_state": "",  # fill in: open / closed_or_blinking / blurry / overexposed / underexposed / misc_not_eye
                "fair_test": "",  # fill in: yes / no
                "notes": "",
            })

        sheet_path = os.path.join(AUDIT_DIR, f"sheet_{sheet_idx:02d}.png")
        cv2.imwrite(sheet_path, canvas)
        print(f"Saved {sheet_path}")

    with open(TEMPLATE_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["global_index", "filename", "detector_success",
                                                "confidence", "visual_eye_state", "fair_test", "notes"])
        writer.writeheader()
        for r in template_rows:
            writer.writerow(r)
    print(f"\nTemplate CSV saved to {TEMPLATE_PATH} ({len(template_rows)} rows)")
    print(f"{n_sheets} contact sheets saved to {AUDIT_DIR}")

if __name__ == "__main__":
    main()
