"""
Drop-in EllSeg-based replacement for pupil_detector.py's detect_pupil().

Same call interface (detect_eye / detect_pupil, same return dict shape) so
gaze_experiment.py and calibration.py can switch detectors by changing one
import line, without rewriting the surrounding logging/plotting/audit logic.

Why this replacement exists: pupil_detector.py's classical Otsu-threshold
method measured 0/20 real success without IR (Stage 6), which is exactly why
Stage 9/10 (gaze_experiment.py / calibration.py) both failed to collect
usable data in their original runs -- there was nothing reliable to average.
EllSeg (7f/7g sections of experiment_report.md) measured a visually-audited
~86% accuracy on the same no-IR, eye-crop hardware setup, both on static
images and on an independently-captured continuous video sequence. This
module wires that validated detector into the same pipeline shape, so the
calibration experiment finally has a detector worth running it with.

Known cost, stated plainly: EllSeg runs at ~7.8 FPS on this machine's CPU
(measured in experiment_report.md 7g.4, full pipeline including I/O), not
the 60-100+ FPS the classical Otsu detector could sustain. A 2.5-3 second
hold period per calibration/gaze target will therefore yield roughly 15-23
samples, not hundreds. This is an intentional trade: fewer but far more
reliable samples beats many samples that were ~0% trustworthy to begin with.

detect_eye() is unchanged (still the same Haar cascade ROI step from
pupil_detector.py) -- only the pupil-center estimation changes.

"contour" in the returned dict is always None here: EllSeg is a direct
ellipse/segmentation regression, it does not produce a classical contour
the way the Otsu pipeline's cv2.findContours step does. Callers must not
assume this field is populated (see the guard added in gaze_experiment.py
and calibration.py's drawing code).
"""
import os
import sys

import cv2
import numpy as np
import torch

# Reuse the exact same Haar cascade detect_eye() as pupil_detector.py --
# no change to the eye-ROI step, only the pupil step is being replaced.
_CASCADE_DIR = r"D:\cv_cascades"  # see 7g.2: project dir moved under a
# Chinese-character path, CascadeClassifier can't open XML there (7d.2/1.3
# recurrence), cascades were copied to this ASCII path as the fix.
_face_cascade = cv2.CascadeClassifier(os.path.join(_CASCADE_DIR, "haarcascade_frontalface_default.xml"))
_eye_cascade = cv2.CascadeClassifier(os.path.join(_CASCADE_DIR, "haarcascade_eye.xml"))


def detect_eye(gray_frame):
    """Returns (x, y, w, h) of one eye ROI in full-frame coordinates, or None.
    Identical logic to pupil_detector.py's detect_eye -- duplicated here
    rather than imported, so this module has no dependency on the Otsu
    detector module it's meant to replace."""
    faces = _face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    if len(faces) == 0:
        return None
    fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray_frame[fy:fy + fh, fx:fx + fw]
    eyes = _eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=8, minSize=(20, 20))
    if len(eyes) == 0:
        return None
    ex, ey, ew, eh = max(eyes, key=lambda e: e[2] * e[3])
    return (fx + ex, fy + ey, ew, eh)


# ---- EllSeg model, loaded once at import time (not per-call) ----
_ELLSEG_DIR = r"C:\Users\34659\AppData\Local\Temp\EllSeg"
sys.path.insert(0, _ELLSEG_DIR)
from models.RITnet_v3 import DenseNet2D          # noqa: E402
from utils import get_predictions                 # noqa: E402
from loss import get_seg2ptLoss                    # noqa: E402
from helperfunctions import my_ellipse             # noqa: E402

_model = DenseNet2D()
_netDict = torch.load(os.path.join(_ELLSEG_DIR, "weights", "all.git_ok"), map_location="cpu")
_model.load_state_dict(_netDict["state_dict"], strict=True)
_model.eval()


def _preprocess_frame(img, op_shape=(240, 320)):
    """Same logic as run_ellseg_video_stability.py's (bugfixed) preprocess_frame
    -- see 7g.3 for why width must be the op_shape constant directly, not
    recomputed via float multiplication (that recomputation can truncate to
    319 instead of 320 due to floating-point error, which crashes the model's
    linear layer on ~2% of real inputs)."""
    sc = op_shape[1] / img.shape[1]
    width = op_shape[1]
    height = int(round(img.shape[0] * sc))
    resized = cv2.resize(img, (width, height), interpolation=cv2.INTER_LANCZOS4)
    pad = op_shape[0] - resized.shape[0]
    if pad > 0:
        top = pad // 2
        resized = np.pad(resized, ((top, pad - top), (0, 0)))
    elif pad < 0:
        crop = -pad
        top = crop // 2
        resized = resized[top: resized.shape[0] - (crop - top), ...]
    norm = (resized - resized.mean()) / (resized.std() + 1e-8)
    t = torch.from_numpy(norm).unsqueeze(0).unsqueeze(0).to(torch.float32)
    return t, sc, pad


def detect_pupil(gray_roi):
    """
    Runs EllSeg on a grayscale eye ROI crop. Returns the same dict shape as
    pupil_detector.py's detect_pupil(): success/reason/pupil_cx/pupil_cy/
    pupil_w/pupil_h/confidence/ellipse/contour.

    "confidence" here is NOT the same quantity as the Otsu detector's
    circularity-based confidence -- EllSeg doesn't expose a natural
    per-frame confidence score, so this is fixed at 1.0 on success, 0.0 on
    failure. Do not compare this number across detectors; only compare
    success/failure and the resulting pupil_cx/pupil_cy coordinates.
    """
    h, w = gray_roi.shape
    result = {
        "success": False,
        "reason": "",
        "pupil_cx": float("nan"),
        "pupil_cy": float("nan"),
        "pupil_w": float("nan"),
        "pupil_h": float("nan"),
        "confidence": 0.0,
        "ellipse": None,
        "contour": None,  # EllSeg has no classical contour -- always None, see module docstring
    }

    if gray_roi.size == 0 or h < 10 or w < 10:
        result["reason"] = "ROI too small"
        return result

    with torch.no_grad():
        t, sc, pad = _preprocess_frame(gray_roi)
        x4, x3, x2, x1, x = _model.enc(t)
        elOut = _model.elReg(x, 0)
        seg_out = _model.dec(x4, x3, x2, x1, x)

        _, norm_pupil_center = get_seg2ptLoss(seg_out[:, 2, ...], torch.zeros(2,), temperature=4)
        H, W = 240, 320
        Hm = np.array([[W / 2, 0, W / 2], [0, H / 2, H / 2], [0, 0, 1]])
        elOut_sq = elOut.squeeze()
        norm_pupil_ellipse = torch.cat([norm_pupil_center.squeeze(0), elOut_sq[7:10]])
        pupil_ellipse = my_ellipse(norm_pupil_ellipse.numpy()).transform(Hm)[0][:-1]

    pupil_ellipse = np.array(pupil_ellipse, dtype=np.float64)
    if np.all(pupil_ellipse == -1) or np.isnan(pupil_ellipse).any():
        result["reason"] = "EllSeg returned no valid pupil ellipse"
        return result

    # undo the resize+pad/crop from _preprocess_frame to get back to
    # gray_roi's original pixel coordinates
    pupil_ellipse[1] -= np.floor(pad // 2)
    pupil_ellipse[:-1] /= sc

    cx, cy, ew, eh, angle_rad = pupil_ellipse
    if ew <= 0 or eh <= 0:
        result["reason"] = f"degenerate ellipse size (w={ew:.1f}, h={eh:.1f})"
        return result

    result["success"] = True
    result["pupil_cx"] = round(float(cx), 2)
    result["pupil_cy"] = round(float(cy), 2)
    result["pupil_w"] = round(float(ew), 2)
    result["pupil_h"] = round(float(eh), 2)
    result["confidence"] = 1.0
    # cv2.ellipse() drawing format: ((cx,cy),(full_w,full_h),angle_degrees)
    result["ellipse"] = ((float(cx), float(cy)), (float(ew), float(eh)), float(np.degrees(angle_rad)))
    return result
