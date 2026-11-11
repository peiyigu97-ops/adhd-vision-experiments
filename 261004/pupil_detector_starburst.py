"""
Starburst-style pupil detector, interface-compatible with pupil_detector.py's
detect_pupil(). Used to compare against the Otsu-threshold baseline on the
same no-IR sample batch (data/eye), per 261010 roadmap section 6.2.

Starburst method (Li et al.): instead of a single global threshold, cast rays
outward from an initial center estimate (here: the darkest-region centroid
from a coarse threshold) in multiple directions, find the pupil-boundary edge
point along each ray via the local gradient, then fit an ellipse to those
boundary points. This is less sensitive to a single global threshold being
wrong under uneven/low-contrast lighting, because each ray only needs a local
gradient jump, not a globally-separable intensity population.

Known limitation going in: this does not fix low signal-to-noise (specular
highlights breaking up the dark region, or sensor noise); it only removes the
dependency on one global threshold. Results must still be visually audited,
not trusted from the success flag alone (see Stage 6 lesson: ellipses pulled
off-center by specular highlights were previously misreported as successes).
"""
import cv2
import numpy as np

CIRCULARITY_THRESHOLD = 0.75
N_RAYS = 36
MIN_RAY_HITS = 18  # at least half the rays must find a boundary edge


def _coarse_center(gray_roi):
    """Rough initial center: centroid of the darkest 5% of pixels."""
    h, w = gray_roi.shape
    thresh_val = np.percentile(gray_roi, 5)
    dark_mask = gray_roi <= thresh_val
    ys, xs = np.nonzero(dark_mask)
    if len(xs) == 0:
        return None
    return float(np.mean(xs)), float(np.mean(ys))


def _cast_rays(gray_roi, cx, cy, n_rays, max_radius):
    """
    For each of n_rays directions from (cx, cy), walk outward along the
    gradient until a strong positive intensity jump (dark->light edge) is
    found. Returns list of (x, y) boundary points, one per ray that found
    an edge.
    """
    h, w = gray_roi.shape
    blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0).astype(np.float32)
    points = []
    for i in range(n_rays):
        theta = 2 * np.pi * i / n_rays
        dx, dy = np.cos(theta), np.sin(theta)
        prev_val = None
        for r in range(1, max_radius):
            x = int(round(cx + dx * r))
            y = int(round(cy + dy * r))
            if x < 0 or x >= w or y < 0 or y >= h:
                break
            val = blurred[y, x]
            if prev_val is not None and (val - prev_val) > 15:
                points.append((x, y))
                break
            prev_val = val
    return points


def detect_pupil(gray_roi):
    """
    Same return contract as pupil_detector.detect_pupil(): a dict with
    success/reason/pupil_cx/pupil_cy/pupil_w/pupil_h/confidence, plus
    ellipse/contour (contour is None here; boundary points stored instead
    for visualization under the 'boundary_points' key).
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
        "boundary_points": None,
    }

    if gray_roi.size == 0 or h < 10 or w < 10:
        result["reason"] = "ROI too small"
        return result

    center = _coarse_center(gray_roi)
    if center is None:
        result["reason"] = "no dark region found for initial center estimate"
        return result
    cx0, cy0 = center

    max_radius = int(min(h, w) * 0.6)
    boundary_points = _cast_rays(gray_roi, cx0, cy0, N_RAYS, max_radius)

    if len(boundary_points) < MIN_RAY_HITS:
        result["reason"] = f"too few ray hits ({len(boundary_points)}/{N_RAYS}) to fit boundary"
        result["boundary_points"] = boundary_points
        return result

    pts = np.array(boundary_points, dtype=np.float32).reshape(-1, 1, 2)
    ellipse = cv2.fitEllipse(pts)
    (cx, cy), (ew, eh), angle = ellipse

    # circularity proxy: ratio of minor/major axis (1.0 = perfect circle)
    major, minor = max(ew, eh), min(ew, eh)
    circularity = minor / major if major > 0 else 0.0

    result["boundary_points"] = boundary_points
    if circularity < CIRCULARITY_THRESHOLD:
        result["reason"] = f"fitted ellipse too elongated (axis ratio {circularity:.2f})"
        result["ellipse"] = ellipse
        return result

    result["success"] = True
    result["pupil_cx"] = round(cx, 2)
    result["pupil_cy"] = round(cy, 2)
    result["pupil_w"] = round(ew, 2)
    result["pupil_h"] = round(eh, 2)
    result["confidence"] = round(min(1.0, circularity), 3)
    result["ellipse"] = ellipse
    return result
