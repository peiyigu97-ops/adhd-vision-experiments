"""
Plan B (261010 roadmap section 6.3) first test: can MediaPipe FaceLandmarker's
iris landmarks locate the pupil, on real full-face no-IR frames (data/face_full)?

This intentionally does NOT use data/eye/*.png -- those are already eye-only
crops with no face context (see capture_full_face.py docstring for why that
would fail at the face-detection stage and give a misleading null result).

mediapipe 1.1.1 only exposes the new Tasks API (no mp.solutions.face_mesh),
so this uses vision.FaceLandmarker with the downloaded face_landmarker.task
model, which includes refined landmarks (468 face points + iris points at
indices 468-477 when output_face_blendshapes / refine not needed -- the task
model bundles iris directly, exposed via face_landmarks list).

Usage:
    python test_mediapipe_iris.py
Output:
    data/results/mediapipe_iris_test.csv
    data/results/mediapipe_iris_contact_sheet.png (overlay of detected iris points)
"""
import os
import glob
import csv
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

_DIR = os.path.dirname(os.path.abspath(__file__))
FACE_DIR = os.path.join(_DIR, "data", "face_full")
RESULTS_DIR = os.path.join(_DIR, "data", "results")
MODEL_PATH = os.path.join(_DIR, "models", "face_landmarker.task")

# Iris landmark indices in the 478-point refined face mesh (MediaPipe convention):
# left eye iris: 468-472, right eye iris: 473-477. Index 468 / 473 are the
# iris center points.
LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473


def imread_unicode(path, flags=cv2.IMREAD_GRAYSCALE):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, flags)


def imwrite_unicode(path, img):
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def main():
    if not os.path.exists(MODEL_PATH):
        print(f"Model not found: {MODEL_PATH}")
        return

    # Pass the model as an in-memory buffer, not model_asset_path: MediaPipe's
    # native C++ loader fails to open model_asset_path when it contains CJK
    # characters (this project tree lives under 作品集/课程/...), the same
    # class of issue documented in compare_algorithms.py for cv2.imread/imwrite,
    # just hitting a different native file-I/O layer. Python's own open()
    # handles the Unicode path fine, so read bytes here and hand them off
    # directly instead of letting MediaPipe resolve the path itself.
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
    tiles = []
    for path in files:
        fname = os.path.basename(path)
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
            rows.append({"filename": fname, "face_detected": False,
                         "left_iris_x": "", "left_iris_y": "",
                         "right_iris_x": "", "right_iris_y": ""})
            cv2.putText(vis, "NO FACE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            print(f"{fname}: no face detected")
        else:
            lm = result.face_landmarks[0]
            lx, ly = lm[LEFT_IRIS_CENTER].x * w, lm[LEFT_IRIS_CENTER].y * h
            rx, ry = lm[RIGHT_IRIS_CENTER].x * w, lm[RIGHT_IRIS_CENTER].y * h
            rows.append({"filename": fname, "face_detected": True,
                         "left_iris_x": round(lx, 1), "left_iris_y": round(ly, 1),
                         "right_iris_x": round(rx, 1), "right_iris_y": round(ry, 1)})
            cv2.circle(vis, (int(lx), int(ly)), 4, (0, 255, 0), -1)
            cv2.circle(vis, (int(rx), int(ry)), 4, (0, 255, 0), -1)
            print(f"{fname}: face OK, left_iris=({lx:.0f},{ly:.0f}) right_iris=({rx:.0f},{ry:.0f})")

        tiles.append(cv2.resize(vis, (320, 180)))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(RESULTS_DIR, "mediapipe_iris_test.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    n_ok = sum(1 for r in rows if r["face_detected"])
    total = len(rows)
    print(f"\nFace+iris detected: {n_ok}/{total} ({100.0*n_ok/total:.1f}%)")
    print(f"Wrote: {csv_path}")

    if tiles:
        cols = 4
        rows_imgs = []
        for i in range(0, len(tiles), cols):
            chunk = tiles[i:i+cols]
            while len(chunk) < cols:
                chunk.append(np.zeros_like(tiles[0]))
            rows_imgs.append(np.hstack(chunk))
        sheet = np.vstack(rows_imgs)
        sheet_path = os.path.join(RESULTS_DIR, "mediapipe_iris_contact_sheet.png")
        imwrite_unicode(sheet_path, sheet)
        print(f"Wrote: {sheet_path}")


if __name__ == "__main__":
    main()
