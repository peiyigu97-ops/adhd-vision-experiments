"""
STEP 8: Initial pupil detection on saved eye ROI images.

Pipeline (classical CV only, no deep learning):
  1. grayscale (already grayscale, but ensure single channel)
  2. Gaussian blur (reduce noise/eyelash texture)
  3. adaptive threshold / Otsu threshold to isolate dark pupil region
  4. morphological open+close (remove small noise, fill small holes from
     specular highlights inside the pupil)
  5. contour detection
  6. candidate filtering by: area, aspect ratio, circularity
  7. ellipse fitting on the best remaining candidate

This is NOT expected to succeed on every image. Known risk factors for this
camera/lighting setup (recorded per project requirement, not hidden):
  - no IR illumination yet -> relies on ambient light only, inconsistent
  - no IR-cut filter -> different reflectance behavior than typical visible-light eye images
  - specular highlights (catchlights) from room lighting can create holes
    inside the dark pupil region, splitting it into multiple contours
  - eyelashes/eyelid shadows can be as dark as the pupil, creating false candidates
  - pupil size/position varies with gaze direction and ROI crop quality
  - some ROI crops from Haar cascade are small/low-resolution, limiting
    contour precision

Outputs:
  - annotated image per input (contour + ellipse + center marked) to data/processed/pupil/
  - a CSV log to data/results/pupil_detection.csv recording, per image:
      success (bool), reason_if_failed, pupil_cx, pupil_cy, pupil_w, pupil_h, confidence
"""
import cv2
import numpy as np
import os
import csv

BASE = os.path.dirname(os.path.abspath(__file__))
EYE_DIR = os.path.join(BASE, "data", "eye")
OUT_DIR = os.path.join(BASE, "data", "processed", "pupil")
RESULTS_DIR = os.path.join(BASE, "data", "results")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def detect_pupil(gray):
    """
    Returns a dict with detection result and diagnostic info.
    """
    h, w = gray.shape
    result = {
        "success": False,
        "reason": "",
        "pupil_cx": float("nan"),
        "pupil_cy": float("nan"),
        "pupil_w": float("nan"),
        "pupil_h": float("nan"),
        "confidence": 0.0,
        "ellipse": None,
        "contour": None,
        "binary": None,
    }

    if gray.size == 0 or h < 10 or w < 10:
        result["reason"] = "ROI too small"
        return result

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Otsu threshold on the darkest region (pupil is the darkest structure in eye ROI)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    result["binary"] = binary

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        result["reason"] = "no dark contour found after threshold"
        return result

    frame_area = h * w
    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.01 * frame_area or area > 0.6 * frame_area:
            continue  # too small (noise) or too large (eyelid/shadow covering whole ROI)
        if len(c) < 5:
            continue  # fitEllipse requires >= 5 points
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = bw / float(bh) if bh > 0 else 0
        if aspect < 0.5 or aspect > 2.0:
            continue  # pupil should be roughly round, reject elongated shapes (eyelid/eyelash lines)
        perimeter = cv2.arcLength(c, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter ** 2)
        candidates.append((c, area, aspect, circularity))

    if not candidates:
        result["reason"] = "contours found but none passed area/aspect filtering (likely eyelid shadow or eyelash noise)"
        return result

    # pick candidate with highest circularity (closest to a true ellipse/circle)
    candidates.sort(key=lambda t: t[3], reverse=True)
    best_c, best_area, best_aspect, best_circ = candidates[0]

    # Threshold raised from 0.5 to 0.75 after visual audit: at 0.5, two detections
    # that passed were confirmed (by eye) to be false positives -- the fitted
    # ellipse was pulled off-center by specular highlights/eyelid shadow rather
    # than tracking the true pupil boundary. Without IR illumination, ambient
    # light produces multiple catchlights inside the pupil that fragment the
    # thresholded region's shape, so only near-perfect circularity is trustworthy.
    if best_circ < 0.75:
        result["reason"] = f"best candidate circularity too low ({best_circ:.2f}) -- likely not a true pupil shape"
        return result

    ellipse = cv2.fitEllipse(best_c)
    (cx, cy), (ew, eh), angle = ellipse

    result["success"] = True
    result["pupil_cx"] = round(cx, 2)
    result["pupil_cy"] = round(cy, 2)
    result["pupil_w"] = round(ew, 2)
    result["pupil_h"] = round(eh, 2)
    result["confidence"] = round(min(1.0, best_circ), 3)
    result["ellipse"] = ellipse
    result["contour"] = best_c
    return result


def main():
    files = sorted(f for f in os.listdir(EYE_DIR) if f.endswith(".png"))
    if not files:
        print(f"No eye ROI images found in {EYE_DIR}")
        return

    rows = []
    success_count = 0

    for fname in files:
        path = os.path.join(EYE_DIR, fname)
        gray = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            print(f"  {fname}: failed to read")
            continue

        res = detect_pupil(gray)

        # build annotated visualization regardless of success/failure
        vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        if res["success"]:
            cv2.ellipse(vis, res["ellipse"], (0, 255, 0), 1)
            cv2.drawContours(vis, [res["contour"]], -1, (255, 0, 0), 1)
            cx, cy = int(res["pupil_cx"]), int(res["pupil_cy"])
            cv2.circle(vis, (cx, cy), 2, (0, 0, 255), -1)
            success_count += 1
            print(f"  {fname}: SUCCESS center=({res['pupil_cx']},{res['pupil_cy']}) "
                  f"size=({res['pupil_w']}x{res['pupil_h']}) confidence={res['confidence']}")
        else:
            cv2.putText(vis, "FAIL", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            print(f"  {fname}: FAILED -- {res['reason']}")

        out_path = os.path.join(OUT_DIR, f"annotated_{fname}")
        cv2.imwrite(out_path, vis)

        rows.append({
            "filename": fname,
            "success": res["success"],
            "reason": res["reason"],
            "pupil_x": res["pupil_cx"],
            "pupil_y": res["pupil_cy"],
            "pupil_width": res["pupil_w"],
            "pupil_height": res["pupil_h"],
            "confidence": res["confidence"],
        })

    csv_path = os.path.join(RESULTS_DIR, "pupil_detection.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "success", "reason", "pupil_x",
                                                "pupil_y", "pupil_width", "pupil_height", "confidence"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    total = len(rows)
    print(f"\n--- Summary ---")
    print(f"  Total images: {total}")
    print(f"  Successful detections: {success_count} ({100.0*success_count/total:.1f}%)")
    print(f"  Failed detections: {total - success_count}")
    print(f"  Annotated images saved to: {OUT_DIR}")
    print(f"  CSV log saved to: {csv_path}")

if __name__ == "__main__":
    main()
