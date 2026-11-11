"""
Plan B (261010 roadmap section 6.3) multi-direction test: does MediaPipe
FaceLandmarker's iris landmark keep tracking across gaze/head directions
(center/left/right/up/down), not just the original centered-gaze batch?

Same approach as test_mediapipe_iris.py, but:
- reads data/face_full_multidir instead of data/face_full
- groups results by direction (parsed from filename prefix face_<dir>_NN.png)
- prints + saves a per-direction detection-rate breakdown

Usage:
    python test_mediapipe_iris_multidir.py
Output:
    data/results/mediapipe_iris_multidir_test.csv
    data/results/mediapipe_iris_multidir_summary.csv
    data/results/mediapipe_iris_multidir_contact_sheet.png
"""
import os
import re
import glob
import csv
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

_DIR = os.path.dirname(os.path.abspath(__file__))
FACE_DIR = os.path.join(_DIR, "data", "face_full_multidir")
RESULTS_DIR = os.path.join(_DIR, "data", "results")
MODEL_PATH = os.path.join(_DIR, "models", "face_landmarker.task")

LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473

DIR_RE = re.compile(r"face_([a-z]+)_\d+\.png$")


def imread_unicode(path, flags=cv2.IMREAD_GRAYSCALE):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, flags)


def imwrite_unicode(path, img):
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def parse_direction(fname):
    m = DIR_RE.search(fname)
    return m.group(1) if m else "unknown"


def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Model not found: {MODEL_PATH}")
        return

    with open(MODEL_PATH, "rb") as f:
        model_bytes = f.read()
    base_options = mp_python.BaseOptions(model_asset_buffer=model_bytes)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1,
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)

    files = sorted(glob.glob(os.path.join(FACE_DIR, "*.png")))
    if not files:
        print(f"No images found in {FACE_DIR}")
        return

    rows = []
    tiles_by_dir = {}
    for path in files:
        fname = os.path.basename(path)
        direction = parse_direction(fname)
        gray = imread_unicode(path)
        if gray is None:
            print(f"skip unreadable: {fname}")
            continue
        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = landmarker.detect(mp_image)
        h, w = gray.shape
        vis = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        if not result.face_landmarks:
            rows.append({"filename": fname, "direction": direction, "face_detected": False,
                         "left_iris_x": "", "left_iris_y": "",
                         "right_iris_x": "", "right_iris_y": ""})
            cv2.putText(vis, "NO FACE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            print(f"{fname}: no face detected")
        else:
            lm = result.face_landmarks[0]
            lx, ly = lm[LEFT_IRIS_CENTER].x * w, lm[LEFT_IRIS_CENTER].y * h
            rx, ry = lm[RIGHT_IRIS_CENTER].x * w, lm[RIGHT_IRIS_CENTER].y * h
            rows.append({"filename": fname, "direction": direction, "face_detected": True,
                         "left_iris_x": round(lx, 1), "left_iris_y": round(ly, 1),
                         "right_iris_x": round(rx, 1), "right_iris_y": round(ry, 1)})
            cv2.circle(vis, (int(lx), int(ly)), 4, (0, 255, 0), -1)
            cv2.circle(vis, (int(rx), int(ry)), 4, (0, 255, 0), -1)
            print(f"{fname}: face OK, left_iris=({lx:.0f},{ly:.0f}) right_iris=({rx:.0f},{ry:.0f})")

        tiles_by_dir.setdefault(direction, []).append(cv2.resize(vis, (320, 180)))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(RESULTS_DIR, "mediapipe_iris_multidir_test.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote: {csv_path}")

    # Per-direction summary
    directions = sorted(tiles_by_dir.keys(), key=lambda d: (d != "center", d))
    summary_rows = []
    print("\nPer-direction detection rate:")
    for d in directions:
        d_rows = [r for r in rows if r["direction"] == d]
        n_ok = sum(1 for r in d_rows if r["face_detected"])
        total = len(d_rows)
        pct = 100.0 * n_ok / total if total else 0.0
        print(f"  {d:8s}: {n_ok}/{total} ({pct:.1f}%)")
        summary_rows.append({"direction": d, "detected": n_ok, "total": total,
                              "pct": round(pct, 1)})

    n_ok = sum(1 for r in rows if r["face_detected"])
    total = len(rows)
    print(f"\nOverall: {n_ok}/{total} ({100.0*n_ok/total:.1f}%)")

    summary_path = os.path.join(RESULTS_DIR, "mediapipe_iris_multidir_summary.csv")
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["direction", "detected", "total", "pct"])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"Wrote: {summary_path}")

    # Contact sheet: one row per direction, tiles in capture order
    if tiles_by_dir:
        cols = max(len(v) for v in tiles_by_dir.values())
        rows_imgs = []
        for d in directions:
            chunk = list(tiles_by_dir[d])
            while len(chunk) < cols:
                chunk.append(np.zeros_like(chunk[0]))
            rows_imgs.append(np.hstack(chunk))
        sheet = np.vstack(rows_imgs)
        sheet_path = os.path.join(RESULTS_DIR, "mediapipe_iris_multidir_contact_sheet.png")
        imwrite_unicode(sheet_path, sheet)
        print(f"Wrote: {sheet_path}")


if __name__ == "__main__":
    main()
