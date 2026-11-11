"""
STEP 10: Basic 5-point calibration experiment.

Shows 5 calibration targets (top-left, top-right, center, bottom-left,
bottom-right) in sequence. User looks at each for ~2.5 seconds. Records
mean pupil_x / pupil_y per target (averaged over valid detections only --
NaN frames are excluded from the mean, not treated as zero).

Fits a 2D affine mapping (linear regression, via least squares -- NOT a
neural network, per project requirement) from (pupil_x, pupil_y) to
(screen_target_x, screen_target_y):

    screen_x = a*pupil_x + b*pupil_y + c
    screen_y = d*pupil_x + e*pupil_y + f

Reports calibration_error as the mean Euclidean distance (in screen pixels)
between predicted and actual target positions, using leave-one-out style
direct fit-then-evaluate on the same 5 points (this is a feasibility check,
not a held-out test set -- documented as such, not overstated).

KNOWN LIMITATION: if fewer than 3 of the 5 targets have any valid pupil
detections (expected given Stage 6 findings), the affine fit is
under-determined or degenerate. This script detects that case and reports
it explicitly rather than forcing a fit on insufficient data.
"""
import cv2
import time
import csv
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pupil_detector import detect_eye, detect_pupil

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE, "data", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Re-verified 2026-10-08 via identify_camera.py: index mapping had flipped
# (was 1=OV9281 on 2026-10-04, now 0=OV9281) after a USB re-enumeration event.
# If captures look wrong (unexpectedly dark, or colored instead of monochrome),
# rerun identify_camera.py to reconfirm before assuming the IR LED is broken.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720
CSV_PATH = os.path.join(RESULTS_DIR, "calibration.csv")
HOLD_SECONDS = 2.5

CUE_WIDTH, CUE_HEIGHT = 800, 600
MARGIN = 80
CALIB_POINTS = {
    "TOP_LEFT": (MARGIN, MARGIN),
    "TOP_RIGHT": (CUE_WIDTH - MARGIN, MARGIN),
    "CENTER": (CUE_WIDTH // 2, CUE_HEIGHT // 2),
    "BOTTOM_LEFT": (MARGIN, CUE_HEIGHT - MARGIN),
    "BOTTOM_RIGHT": (CUE_WIDTH - MARGIN, CUE_HEIGHT - MARGIN),
}


def fit_affine(pupil_pts, screen_pts):
    """
    pupil_pts, screen_pts: Nx2 arrays.
    Solves screen = A @ [pupil_x, pupil_y, 1] for a 2x3 matrix A via least squares.
    Returns A (2x3) or None if underdetermined.
    """
    n = len(pupil_pts)
    if n < 3:
        return None
    ones = np.ones((n, 1))
    X = np.hstack([pupil_pts, ones])  # Nx3
    # solve for each screen dimension independently
    A = np.zeros((2, 3))
    for dim in range(2):
        y = screen_pts[:, dim]
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        A[dim, :] = coeffs
    return A


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    csv_file = open(CSV_PATH, "w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow(["timestamp", "point_name", "screen_x", "screen_y", "pupil_x", "pupil_y", "confidence"])

    cv2.namedWindow("Calibration", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Calibration", CUE_WIDTH, CUE_HEIGHT)

    per_point_samples = {name: [] for name in CALIB_POINTS}

    print("Starting 5-point calibration. Look at each dot for 2.5 seconds.")

    for name, (sx, sy) in CALIB_POINTS.items():
        print(f"  Point: {name} at screen ({sx},{sy})")
        start = time.time()
        while time.time() - start < HOLD_SECONDS:
            cue_img = np.zeros((CUE_HEIGHT, CUE_WIDTH, 3), dtype=np.uint8)
            cv2.circle(cue_img, (sx, sy), 20, (0, 255, 0), -1)
            cv2.imshow("Calibration", cue_img)
            cv2.waitKey(1)

            ret, frame = cap.read()
            if not ret:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            ts = time.time()

            pupil_x, pupil_y, conf = float("nan"), float("nan"), 0.0
            roi = detect_eye(gray)
            if roi is not None:
                x, y, w, h = roi
                eye_gray = gray[y:y + h, x:x + w]
                pres = detect_pupil(eye_gray)
                if pres["success"]:
                    pupil_x, pupil_y, conf = pres["pupil_cx"], pres["pupil_cy"], pres["confidence"]
                    per_point_samples[name].append((pupil_x, pupil_y))

            writer.writerow([f"{ts:.3f}", name, sx, sy, pupil_x, pupil_y, conf])

    cap.release()
    cv2.destroyAllWindows()
    csv_file.close()

    print("\n--- Per-point valid sample counts ---")
    pupil_means = {}
    for name, samples in per_point_samples.items():
        print(f"  {name}: {len(samples)} valid samples")
        if samples:
            arr = np.array(samples)
            pupil_means[name] = (float(np.mean(arr[:, 0])), float(np.mean(arr[:, 1])))

    usable_points = [name for name in CALIB_POINTS if name in pupil_means]
    print(f"\n{len(usable_points)}/5 points have usable pupil data.")

    if len(usable_points) < 3:
        print("\nCALIBRATION FAILED: fewer than 3 points have valid pupil detections.")
        print("Cannot fit a 2D affine mapping with fewer than 3 points.")
        print("This is consistent with Stage 6 findings: without IR illumination,")
        print("pupil detection on this hardware is not reliable enough for calibration.")
        return

    pupil_pts = np.array([pupil_means[n] for n in usable_points])
    screen_pts = np.array([CALIB_POINTS[n] for n in usable_points])

    A = fit_affine(pupil_pts, screen_pts)

    predicted = np.hstack([pupil_pts, np.ones((len(pupil_pts), 1))]) @ A.T
    errors = np.linalg.norm(predicted - screen_pts, axis=1)
    mean_error = float(np.mean(errors))

    print(f"\nAffine mapping fit using {len(usable_points)} points.")
    print(f"Per-point prediction error (pixels): {dict(zip(usable_points, np.round(errors, 1)))}")
    print(f"Mean calibration_error: {mean_error:.1f} pixels")
    print("\nNOTE: this error is measured by fitting and evaluating on the SAME")
    print("5 points (feasibility check), not a held-out test set. Reported as such.")

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(screen_pts[:, 0], screen_pts[:, 1], color="green", s=100, label="Target", marker="o")
    ax.scatter(predicted[:, 0], predicted[:, 1], color="red", s=100, label="Predicted", marker="x")
    for i, name in enumerate(usable_points):
        ax.annotate(name, (screen_pts[i, 0], screen_pts[i, 1]))
    ax.set_xlabel("Screen X (pixels)")
    ax.set_ylabel("Screen Y (pixels)")
    ax.set_title(f"Calibration result (mean error: {mean_error:.1f} px, {len(usable_points)}/5 points)")
    ax.invert_yaxis()
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "calibration_result.png"), dpi=120)
    plt.close(fig)

    print(f"\nPlot saved to {os.path.join(RESULTS_DIR, 'calibration_result.png')}")

if __name__ == "__main__":
    main()
