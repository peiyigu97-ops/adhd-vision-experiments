"""
Runs both pupil detectors (Otsu baseline vs starburst) on the same no-IR
sample batch (data/eye/*.png) and writes a side-by-side CSV, plus contact
sheets for visual audit -- per 261010 roadmap section 6.2.

This does NOT re-collect data. It re-uses the exact 20 frames already
captured under no-IR conditions in Stage 6 (same batch pupil_detection.csv
already reports 0/20 for the Otsu method), so the comparison isolates the
algorithm as the only variable.

Usage:
    python compare_algorithms.py
Outputs:
    data/results/algorithm_comparison.csv
    data/results/algorithm_comparison_contact_sheet.png  (visual audit grid)
"""
import os
import glob
import csv
import cv2
import numpy as np

import pupil_detector as otsu_detector
import pupil_detector_starburst as starburst_detector

_DIR = os.path.dirname(os.path.abspath(__file__))
EYE_DIR = os.path.join(_DIR, "data", "eye")
RESULTS_DIR = os.path.join(_DIR, "data", "results")


def imread_unicode(path, flags=cv2.IMREAD_GRAYSCALE):
    """cv2.imread fails silently on non-ASCII (CJK) Windows paths; read via
    numpy buffer instead, since this whole project tree lives under a
    Chinese-character path (作品集/课程/...)."""
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, flags)


def imwrite_unicode(path, img):
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def draw_overlay(gray_roi, result, color):
    vis = cv2.cvtColor(gray_roi, cv2.COLOR_GRAY2BGR)
    if result.get("ellipse") is not None:
        cv2.ellipse(vis, result["ellipse"], color, 2)
    pts = result.get("boundary_points")
    if pts:
        for (x, y) in pts:
            cv2.circle(vis, (int(x), int(y)), 1, color, -1)
    label = "OK" if result["success"] else "FAIL"
    cv2.putText(vis, label, (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    return vis


def main():
    files = sorted(glob.glob(os.path.join(EYE_DIR, "*.png")))
    if not files:
        print(f"No sample images found in {EYE_DIR}")
        return

    rows = []
    tiles = []
    for path in files:
        fname = os.path.basename(path)
        img = imread_unicode(path)
        if img is None:
            print(f"skip unreadable: {fname}")
            continue

        otsu_result = otsu_detector.detect_pupil(img)
        star_result = starburst_detector.detect_pupil(img)

        rows.append({
            "filename": fname,
            "otsu_success": otsu_result["success"],
            "otsu_reason": otsu_result["reason"],
            "otsu_confidence": otsu_result["confidence"],
            "starburst_success": star_result["success"],
            "starburst_reason": star_result["reason"],
            "starburst_confidence": star_result["confidence"],
        })

        otsu_vis = draw_overlay(img, otsu_result, (0, 0, 255))
        star_vis = draw_overlay(img, star_result, (0, 255, 0))
        pair = np.hstack([otsu_vis, star_vis])
        tiles.append(pair)

        print(f"{fname}: otsu={otsu_result['success']} starburst={star_result['success']}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(RESULTS_DIR, "algorithm_comparison.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    otsu_n = sum(1 for r in rows if r["otsu_success"])
    star_n = sum(1 for r in rows if r["starburst_success"])
    total = len(rows)
    print(f"\nOtsu (baseline, no-IR):      {otsu_n}/{total} ({100.0*otsu_n/total:.1f}%)")
    print(f"Starburst (new, no-IR):      {star_n}/{total} ({100.0*star_n/total:.1f}%)")
    print(f"Reference, Otsu + 850nm IR:  27.2% (22/81, from Stage 6, different batch)")
    print(f"\nWrote: {csv_path}")

    # contact sheet: stack all pairs vertically, resize each tile to a
    # common width for readability
    target_w = 480
    resized = []
    for t in tiles:
        h, w = t.shape[:2]
        scale = target_w / w
        resized.append(cv2.resize(t, (target_w, int(h * scale))))
    sheet = np.vstack(resized)
    sheet_path = os.path.join(RESULTS_DIR, "algorithm_comparison_contact_sheet.png")
    imwrite_unicode(sheet_path, sheet)
    print(f"Wrote: {sheet_path}  (red=Otsu overlay, green=starburst overlay, left/right per row)")
    print("\nNEXT STEP: visually audit the contact sheet. A 'success' flag from either")
    print("algorithm is not proof of a correct detection -- confirm the ellipse/points")
    print("actually sit on the pupil, not on a specular highlight or eyelid edge.")


if __name__ == "__main__":
    main()
