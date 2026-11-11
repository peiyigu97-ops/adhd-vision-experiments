"""
GC0308 module - detector variant with median-filter noise suppression.

Same pipeline as pupil_detector_base.detect_pupil, with ONE addition: a
median blur pass before the Gaussian blur + Otsu threshold. Median filtering
is well suited to the granular "salt-and-pepper"-like speckle noise observed
on this sensor's skin-tone regions (see gc0308_pupil_test_cropped.py results:
circularity jumped from ~0.1 to ~0.4-0.6 after cropping out the nose bridge,
but residual noise at the crop edges still dragged candidates below the 0.75
threshold). Median blur suppresses that kind of impulse-like noise without
smearing true edges as much as a larger Gaussian kernel would.

This is a SEPARATE file from pupil_detector_base.py (used by OV9281 tests)
specifically so the OV9281 numbers in the report are not retroactively
changed by a GC0308-motivated tweak -- keeps the two hardware lines'
results comparable to what was actually measured for each.
"""
import cv2
import numpy as np

CIRCULARITY_THRESHOLD = 0.75


def detect_pupil(gray_roi):
    h, w = gray_roi.shape
    result = {
        "success": False, "reason": "", "pupil_cx": float("nan"), "pupil_cy": float("nan"),
        "pupil_w": float("nan"), "pupil_h": float("nan"), "confidence": 0.0,
        "ellipse": None, "contour": None,
    }
    if gray_roi.size == 0 or h < 10 or w < 10:
        result["reason"] = "ROI too small"
        return result

    # NEW STEP vs. pupil_detector_base: median blur to suppress granular
    # sensor noise before the usual Gaussian blur + Otsu pipeline.
    denoised = cv2.medianBlur(gray_roi, 5)
    blurred = cv2.GaussianBlur(denoised, (5, 5), 0)

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
