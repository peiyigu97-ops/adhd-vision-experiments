"""
Shared pupil/eye detection module used by stages 5-10.

Centralizing this logic means that once IR illumination hardware arrives and
a better detector is needed (e.g. a different threshold strategy, or IR-specific
preprocessing), only this file needs to change -- the real-time tracking,
logging, gaze experiment, and calibration scripts all import from here and
don't need to be rewritten.

Current implementation is classical CV only (no deep learning), using the
same Otsu threshold + contour + ellipse-fit pipeline validated in Stage 6,
with the circularity threshold (0.75) that was empirically raised after a
visual audit showed lower thresholds produced false-positive "successes"
(ellipses pulled off the true pupil center by specular highlights).

Known limitation (see Stage 6 report): under current hardware (no IR
illuminator, no IR-cut filter, ambient light only), this detector's real
success rate measured on saved ROI samples was 0/20. It is wired into the
realtime pipeline anyway so that the pipeline itself is validated end-to-end
(ROI -> detection -> logging -> plotting), with NaN/confidence=0 propagating
correctly when detection fails, rather than silently faking data.
"""
import cv2
import numpy as np
import os

_CASCADE_DIR = os.path.dirname(os.path.abspath(__file__))
_face_cascade = cv2.CascadeClassifier(os.path.join(_CASCADE_DIR, "haarcascade_frontalface_default.xml"))
_eye_cascade = cv2.CascadeClassifier(os.path.join(_CASCADE_DIR, "haarcascade_eye.xml"))

CIRCULARITY_THRESHOLD = 0.75


def detect_eye(gray_frame):
    """Returns (x, y, w, h) of one eye ROI in full-frame coordinates, or None."""
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


def detect_pupil(gray_roi):
    """
    Runs classical threshold/contour/ellipse-fit pupil detection on a grayscale
    eye ROI crop. Returns a dict always containing success/reason/pupil_cx/
    pupil_cy/pupil_w/pupil_h/confidence, plus ellipse/contour/binary for
    visualization when success is True.
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
        "contour": None,
    }

    if gray_roi.size == 0 or h < 10 or w < 10:
        result["reason"] = "ROI too small"
        return result

    blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        result["reason"] = "no dark contour found after threshold"
        return result

    frame_area = h * w
    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 0.01 * frame_area or area > 0.6 * frame_area:
            continue
        if len(c) < 5:
            continue
        bx, by, bw, bh = cv2.boundingRect(c)
        aspect = bw / float(bh) if bh > 0 else 0
        if aspect < 0.5 or aspect > 2.0:
            continue
        perimeter = cv2.arcLength(c, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter ** 2)
        candidates.append((c, area, aspect, circularity))

    if not candidates:
        result["reason"] = "contours found but none passed area/aspect filtering"
        return result

    candidates.sort(key=lambda t: t[3], reverse=True)
    best_c, best_area, best_aspect, best_circ = candidates[0]

    if best_circ < CIRCULARITY_THRESHOLD:
        result["reason"] = f"best candidate circularity too low ({best_circ:.2f})"
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
