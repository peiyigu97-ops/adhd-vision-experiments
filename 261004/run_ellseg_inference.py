"""
EllSeg (RSKothari/EllSeg) inference on the existing no-IR eye-crop batch
(data/eye/*.png, 20 frames, same batch already tested with Otsu threshold
method [0/20, pupil_detection.csv] and starburst method [program 30%,
visually audited ~2/20] in experiment_report.md 7d.2).

This script does NOT retrain anything. It loads the official pretrained
checkpoint `weights/all.git_ok` ("All datasets", recommended for deployment
per the repo README) into the RITnet_v3 architecture (DenseElNet, the
architecture EllSeg's own evaluate_ellseg.py hardcodes as default), runs a
forward pass per image, and saves an overlay PNG per image for manual visual
audit -- per this project's established methodology (see report section 6.3,
7a.4, 7d.2): a program-reported "success" number is never trusted on its own.

The repo's own evaluate_ellseg.py only accepts .mp4 videos as input. The
preprocessing/postprocessing logic inside it (preprocess_frame,
evaluate_ellseg_on_image, rescale_to_original) is reused as-is here, just
fed from a folder of PNGs instead of a video decoder.

Usage:
    python run_ellseg_inference.py
Outputs:
    data/results/ellseg/<filename>_overlay.png   per-image overlay (for audit)
    data/results/ellseg_results.csv              per-image numeric output
    data/results/ellseg_contact_sheet.png         all 20 overlays in one grid
"""
import os
import csv
import copy
import glob

import cv2
import numpy as np
import torch

ELLSEG_DIR = r"C:\Users\34659\AppData\Local\Temp\EllSeg"
PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
EYE_DIR = os.path.join(PROJ_DIR, "data", "eye")
RESULTS_DIR = os.path.join(PROJ_DIR, "data", "results")
OVERLAY_DIR = os.path.join(RESULTS_DIR, "ellseg")

import sys
sys.path.insert(0, ELLSEG_DIR)

# NOTE: we deliberately do NOT `from modelSummary import model_dict` here.
# modelSummary.py eagerly instantiates all 8 architectures (ritnet_v1..v7 +
# deepvog) at import time, and RITnet_v7.py still has an unpatched
# `np.int(...)` call (numpy>=1.24 removed this alias) that a tool-side
# safety classifier is currently refusing to let us edit in this session
# (confirmed file-specific, not a global block -- other edits still work).
# We only need ritnet_v3 (the architecture evaluate_ellseg.py itself
# hardcodes as default), so import it directly and skip the other 7.
from models.RITnet_v3 import DenseNet2D as _DenseNet2D_v3  # noqa: E402
from utils import get_predictions                  # noqa: E402
from loss import get_seg2ptLoss                     # noqa: E402
from helperfunctions import plot_segmap_ellpreds    # noqa: E402
from helperfunctions import ransac, ElliFit, getValidPoints, my_ellipse  # noqa: E402


# ---- Chinese-path-safe image I/O (established pattern, see
# compare_algorithms.py imread_unicode/imwrite_unicode: cv2.imread/imwrite
# silently fail on non-ASCII Windows paths; this whole project tree lives
# under 作品集/课程/...) ----
def imread_unicode(path, flags=cv2.IMREAD_GRAYSCALE):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, flags)


def imwrite_unicode(path, img):
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


# ---- preprocessing, copied from evaluate_ellseg.py (unmodified logic) ----
def preprocess_frame(img, op_shape, align_width=True):
    if align_width:
        if op_shape[1] != img.shape[1]:
            sc = op_shape[1] / img.shape[1]
            width = int(img.shape[1] * sc)
            height = int(img.shape[0] * sc)
            img = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)

            if op_shape[0] > img.shape[0]:
                pad_width = op_shape[0] - img.shape[0]
                if pad_width % 2 == 0:
                    img = np.pad(img, ((pad_width // 2, pad_width // 2), (0, 0)))
                else:
                    img = np.pad(img, ((pad_width // 2, pad_width // 2 + 1), (0, 0)))
                scale_shift = (sc, pad_width)
            elif op_shape[0] < img.shape[0]:
                pad_width = op_shape[0] - img.shape[0]  # negative
                crop = -pad_width
                top = crop // 2
                bottom = crop - top
                img = img[top: img.shape[0] - bottom, ...]
                scale_shift = (sc, pad_width)
            else:
                scale_shift = (sc, 0)
        else:
            scale_shift = (1, 0)
    else:
        raise RuntimeError("Height alignment not implemented")

    img = (img - img.mean()) / (img.std() + 1e-8)
    img_t = torch.from_numpy(img).unsqueeze(0).to(torch.float32)
    return img_t, scale_shift


def evaluate_ellseg_on_image(frame, model, ellseg_ellipses=1):
    assert len(frame.shape) == 4, 'Frame must be [1,1,H,W]'
    with torch.no_grad():
        x4, x3, x2, x1, x = model.enc(frame)
        latent = torch.mean(x.flatten(start_dim=2), -1)
        elOut = model.elReg(x, 0)
        seg_out = model.dec(x4, x3, x2, x1, x)

    seg_out_cpu, elOut_cpu, latent = seg_out.cpu(), elOut.squeeze().cpu(), latent.squeeze().cpu()
    seg_map = get_predictions(seg_out_cpu).squeeze().numpy()

    if ellseg_ellipses == 1:
        # Ellipse derived from EllSeg's own latent-space regression head
        _, norm_pupil_center = get_seg2ptLoss(seg_out_cpu[:, 2, ...], torch.zeros(2, ), temperature=4)
        _, norm_iris_center = get_seg2ptLoss(-seg_out_cpu[:, 0, ...], torch.zeros(2, ), temperature=4)

        norm_pupil_ellipse = torch.cat([norm_pupil_center, elOut_cpu[7:10]])
        norm_iris_ellipse = torch.cat([norm_iris_center, elOut_cpu[2:5]])

        _, _, H, W = frame.shape
        Hm = np.array([[W / 2, 0, W / 2], [0, H / 2, H / 2], [0, 0, 1]])

        pupil_ellipse = my_ellipse(norm_pupil_ellipse.numpy()).transform(Hm)[0][:-1]
        iris_ellipse = my_ellipse(norm_iris_ellipse.numpy()).transform(Hm)[0][:-1]
    else:
        # Ellipse fit (RANSAC ElliFit) directly on the segmentation mask
        seg_map_temp = copy.deepcopy(seg_map)
        seg_map_temp[seg_map_temp == 2] += 1
        seg_map_temp[seg_map_temp == 1] += 1

        pupilPts, irisPts = getValidPoints(seg_map_temp, isPartSeg=False)

        if np.sum(seg_map_temp == 3) > 50 and type(pupilPts) is not list:
            model_pupil = ransac(pupilPts, ElliFit, 15, 40, 5e-3, 15).loop()
        else:
            model_pupil = type('model', (object,), {})
            model_pupil.model = np.array([-1, -1, -1, -1, -1])

        if np.sum(seg_map_temp == 2) > 50 and type(irisPts) is not list:
            model_iris = ransac(irisPts, ElliFit, 15, 40, 5e-3, 15).loop()
        else:
            model_iris = type('model', (object,), {})
            model_iris.model = np.array([-1, -1, -1, -1, -1])

        pupil_ellipse = np.array(model_pupil.model)
        iris_ellipse = np.array(model_iris.model)

    return seg_map, latent.numpy(), np.array(pupil_ellipse, dtype=np.float64), np.array(iris_ellipse, dtype=np.float64)


def rescale_to_original(seg_map, pupil_ellipse, iris_ellipse, scale_shift, orig_shape):
    if not np.all(pupil_ellipse == -1):
        pupil_ellipse[1] = pupil_ellipse[1] - np.floor(scale_shift[1] // 2)
        pupil_ellipse[:-1] = pupil_ellipse[:-1] * (1 / scale_shift[0])
    if not np.all(iris_ellipse == -1):
        iris_ellipse[1] = iris_ellipse[1] - np.floor(scale_shift[1] // 2)
        iris_ellipse[:-1] = iris_ellipse[:-1] * (1 / scale_shift[0])

    if scale_shift[1] < 0:
        pad = int(-scale_shift[1] // 2)
        seg_map = np.pad(seg_map, ((pad, pad), (0, 0)))
    elif scale_shift[1] > 0:
        pad = int(scale_shift[1] // 2)
        if pad > 0:
            seg_map = seg_map[pad:-pad, ...]

    seg_map = cv2.resize(seg_map.astype(np.uint8), (orig_shape[1], orig_shape[0]), interpolation=cv2.INTER_NEAREST)
    return seg_map, pupil_ellipse, iris_ellipse


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(OVERLAY_DIR, exist_ok=True)

    loadfile = os.path.join(ELLSEG_DIR, "weights", "all.git_ok")
    print(f"Loading checkpoint: {loadfile}")
    netDict = torch.load(loadfile, map_location="cpu")

    model = _DenseNet2D_v3()
    model.load_state_dict(netDict['state_dict'], strict=True)
    model.eval()
    device = torch.device("cpu")
    model = model.to(device)

    files = sorted(glob.glob(os.path.join(EYE_DIR, "*.png")))
    print(f"Found {len(files)} images in {EYE_DIR}")

    rows = []
    overlays = []

    for path in files:
        fname = os.path.basename(path)
        img = imread_unicode(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"  [skip] failed to read {fname}")
            continue

        orig_shape = img.shape

        if img.max() < 20:
            print(f"  [skip] {fname} too dark (max={img.max()})")
            rows.append({"filename": fname, "pupil_found": False, "iris_found": False,
                         "pupil_cx": "", "pupil_cy": "", "reason": "frame too dark"})
            continue

        frame_t, scale_shift = preprocess_frame(img.copy(), (240, 320), align_width=True)
        input_tensor = frame_t.unsqueeze(0).to(device)

        seg_map, latent, pupil_ellipse, iris_ellipse = evaluate_ellseg_on_image(
            input_tensor, model, ellseg_ellipses=1)

        seg_map, pupil_ellipse, iris_ellipse = rescale_to_original(
            seg_map, pupil_ellipse, iris_ellipse, scale_shift, orig_shape)

        overlay = plot_segmap_ellpreds(img, seg_map, pupil_ellipse, iris_ellipse)
        overlay_bgr = overlay[..., ::-1].astype(np.uint8)  # RGB->BGR for cv2 save

        overlay_path = os.path.join(OVERLAY_DIR, os.path.splitext(fname)[0] + "_overlay.png")
        imwrite_unicode(overlay_path, overlay_bgr)
        overlays.append((fname, overlay_bgr))

        pupil_found = not np.all(pupil_ellipse == -1)
        iris_found = not np.all(iris_ellipse == -1)

        rows.append({
            "filename": fname,
            "pupil_found": pupil_found,
            "iris_found": iris_found,
            "pupil_cx": round(float(pupil_ellipse[0]), 2) if pupil_found else "",
            "pupil_cy": round(float(pupil_ellipse[1]), 2) if pupil_found else "",
            "pupil_w": round(float(pupil_ellipse[2]), 2) if pupil_found else "",
            "pupil_h": round(float(pupil_ellipse[3]), 2) if pupil_found else "",
            "iris_cx": round(float(iris_ellipse[0]), 2) if iris_found else "",
            "iris_cy": round(float(iris_ellipse[1]), 2) if iris_found else "",
            "reason": "",
        })

        print(f"  {fname}: pupil_found={pupil_found} iris_found={iris_found} "
              f"pupil_c=({pupil_ellipse[0]:.1f},{pupil_ellipse[1]:.1f})" if pupil_found else
              f"  {fname}: pupil_found=False iris_found={iris_found}")

    # --- CSV ---
    csv_path = os.path.join(RESULTS_DIR, "ellseg_results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["filename", "pupil_found", "iris_found",
                                                "pupil_cx", "pupil_cy", "pupil_w", "pupil_h",
                                                "iris_cx", "iris_cy", "reason"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {csv_path}")

    n_total = len(rows)
    n_pupil = sum(1 for r in rows if r["pupil_found"])
    print(f"Program-reported pupil detection: {n_pupil}/{n_total} "
          f"({100.0*n_pupil/n_total:.1f}%)  -- NOT a final number, needs visual audit")

    # --- contact sheet for visual audit ---
    if overlays:
        thumb = 160
        per_row = 5
        n = len(overlays)
        n_rows = (n + per_row - 1) // per_row
        sheet = np.zeros((n_rows * (thumb + 20), per_row * thumb, 3), dtype=np.uint8)
        for i, (fname, img_bgr) in enumerate(overlays):
            r, c = divmod(i, per_row)
            resized = cv2.resize(img_bgr, (thumb, thumb), interpolation=cv2.INTER_NEAREST)
            y0 = r * (thumb + 20)
            x0 = c * thumb
            sheet[y0:y0 + thumb, x0:x0 + thumb] = resized
            cv2.putText(sheet, f"#{i}", (x0 + 3, y0 + thumb + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        sheet_path = os.path.join(RESULTS_DIR, "ellseg_contact_sheet.png")
        imwrite_unicode(sheet_path, sheet)
        print(f"Wrote {sheet_path}")


if __name__ == "__main__":
    main()
