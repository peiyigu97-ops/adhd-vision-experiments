"""
STEP 9: Basic relative gaze experiment (left/center/right/up/down).

Displays a target cue window in sequence: LEFT, CENTER, RIGHT, UP, DOWN.
User keeps head still and looks at each on-screen cue for ~3 seconds while
OV9281 + pupil_detector runs in the background. Logs every sample (including
NaN rows when detection fails) to data/results/pupil_tracking.csv with an
extra "target" column marking which direction was being shown.

CHANGES 2026-10-09 round 2 (after 4 runs with manually-adjusted/uncertain IR
lighting state gave wildly different hit rates and the IR on/off status for
each run could not be reliably recalled afterward):
  Added save_success_frames: every time detect_pupil() succeeds, the
  annotated eye-ROI crop (ellipse + contour + center dot, same style as
  Stage 6/6c's annotated_*.png) is saved to data/results/gaze_exp_audit/.
  This closes the same gap that let Stage 6's original 10% number get
  wrongly trusted at first -- a success percentage must never be reported
  without the ability to visually audit it afterward. It also lets us check
  after the fact whether a given run's successes look like genuine pupil
  detections or specular-highlight false positives, independent of whatever
  the IR light was doing during that run.

CHANGES 2026-10-09 round 1 (after 3 runs gave wildly different hit rates:
0%, 9.0%, 12.7%, and the user reported "I couldn't tell if the camera was
even pointed at my eye" on the third run):
  1. Added a live "Eye ROI" preview window (same mechanism as Stage 7's
     eye_tracking_realtime.py) so the user can see in real time whether the
     camera is actually tracking the eye, instead of staring at a blank cue
     window with no feedback. This directly addresses the reported issue.
  2. Added a roi_found column to the CSV, matching eye_tracking_realtime.py's
     2026-10-09 fix, so "Haar cascade didn't find an eye" and "eye found but
     pupil detection failed" can be told apart -- the previous 0%/9.0%/12.7%
     numbers conflated both failure modes and are not directly comparable to
     Stage 5 (15.5% ROI) or Stage 6c (27.2% pupil-given-ROI).

After the session, generates two plots (per project requirement -- labeled
"relative pupil position", NOT "absolute gaze coordinates", since no
calibration has been performed yet):
  1. pupil_x vs time (data/results/pupil_trajectory.png, time-series)
  2. pupil_x vs pupil_y (scatter, colored by target direction)

The plots and this script do not hide gaps -- if detection rate is too low,
the trajectory plot will show large gaps rather than a smoothed/interpolated
fake signal.
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
AUDIT_DIR = os.path.join(RESULTS_DIR, "gaze_exp_audit")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(AUDIT_DIR, exist_ok=True)

# Re-verified 2026-10-08 via identify_camera.py: index mapping had flipped
# (was 1=OV9281 on 2026-10-04, now 0=OV9281) after a USB re-enumeration event.
# If captures look wrong (unexpectedly dark, or colored instead of monochrome),
# rerun identify_camera.py to reconfirm before assuming the IR LED is broken.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720
CSV_PATH = os.path.join(RESULTS_DIR, "pupil_tracking.csv")
HOLD_SECONDS = 3.0

TARGETS = ["LEFT", "CENTER", "RIGHT", "UP", "DOWN"]

CUE_WIDTH, CUE_HEIGHT = 800, 600
CUE_POSITIONS = {
    "LEFT": (100, 300),
    "CENTER": (400, 300),
    "RIGHT": (700, 300),
    "UP": (400, 80),
    "DOWN": (400, 520),
}


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    csv_file = open(CSV_PATH, "w", newline="")
    writer = csv.writer(csv_file)
    writer.writerow(["timestamp", "frame", "target", "roi_found", "pupil_x", "pupil_y", "confidence", "audit_image"])

    cv2.namedWindow("Gaze Target", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Gaze Target", CUE_WIDTH, CUE_HEIGHT)

    frame_idx = 0
    roi_hits = 0
    pupil_hits = 0
    rows = []

    print("Starting 5-point relative gaze experiment.")
    print("Keep head still, look at each on-screen dot for 3 seconds.")
    print("Watch the 'Eye ROI' window to confirm the camera is tracking your eye.")
    print(f"Every successful detection saves an audit image to {AUDIT_DIR}")

    for target in TARGETS:
        print(f"  Target: {target}")
        start = time.time()
        while time.time() - start < HOLD_SECONDS:
            cue_img = np.zeros((CUE_HEIGHT, CUE_WIDTH, 3), dtype=np.uint8)
            px, py = CUE_POSITIONS[target]
            cv2.circle(cue_img, (px, py), 20, (0, 0, 255), -1)
            cv2.putText(cue_img, target, (px - 30, py - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow("Gaze Target", cue_img)

            ret, frame = cap.read()
            if not ret:
                cv2.waitKey(1)
                continue
            frame_idx += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            ts = time.time()

            pupil_x, pupil_y, conf = float("nan"), float("nan"), 0.0
            audit_fname = ""
            roi = detect_eye(gray)
            roi_found = roi is not None

            if roi is not None:
                roi_hits += 1
                x, y, w, h = roi
                eye_gray = gray[y:y + h, x:x + w]
                pres = detect_pupil(eye_gray)

                eye_vis = cv2.cvtColor(eye_gray, cv2.COLOR_GRAY2BGR)
                if pres["success"]:
                    pupil_hits += 1
                    pupil_x, pupil_y, conf = pres["pupil_cx"], pres["pupil_cy"], pres["confidence"]
                    cv2.ellipse(eye_vis, pres["ellipse"], (0, 255, 0), 1)
                    cv2.drawContours(eye_vis, [pres["contour"]], -1, (255, 0, 0), 1)
                    cx, cy = int(pres["pupil_cx"]), int(pres["pupil_cy"])
                    cv2.circle(eye_vis, (cx, cy), 2, (0, 0, 255), -1)

                    # Save for later visual audit -- never trust a success
                    # percentage without the ability to check it afterward
                    # (this is the exact gap that caused Stage 6's original
                    # 10% number to be wrongly trusted before visual review).
                    audit_fname = f"{target}_{frame_idx}_{int(ts*1000)}.png"
                    cv2.imwrite(os.path.join(AUDIT_DIR, audit_fname), eye_vis)

                cv2.imshow("Eye ROI", eye_vis)
            else:
                # show a blank placeholder so the window doesn't just vanish,
                # making "camera lost the eye" visually obvious rather than silent
                blank = np.zeros((100, 100, 3), dtype=np.uint8)
                cv2.putText(blank, "NO EYE", (5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                cv2.imshow("Eye ROI", blank)

            cv2.waitKey(1)

            writer.writerow([f"{ts:.3f}", frame_idx, target, roi_found, pupil_x, pupil_y, conf, audit_fname])
            rows.append({"t": ts, "frame": frame_idx, "target": target, "x": pupil_x, "y": pupil_y, "conf": conf})

    cap.release()
    cv2.destroyAllWindows()
    csv_file.close()

    total = len(rows)
    valid = [r for r in rows if not np.isnan(r["x"])]
    roi_rate = 100.0 * roi_hits / total if total else 0.0
    pupil_given_roi_rate = 100.0 * pupil_hits / roi_hits if roi_hits else 0.0

    print(f"\nSession summary:")
    print(f"  Total frames: {total}")
    print(f"  Eye-ROI hit rate (comparable to Stage 5's 15.5% / Stage 7's 15.17%): {roi_rate:.1f}% ({roi_hits}/{total})")
    print(f"  Pupil detect rate GIVEN a found ROI (comparable to Stage 6c's 27.2% / Stage 7's 30.16%): "
          f"{pupil_given_roi_rate:.1f}% ({pupil_hits}/{roi_hits})")
    print(f"  Pupil detect rate of ALL frames: {100.0*len(valid)/total:.1f}% ({len(valid)}/{total})")
    print(f"  UNVERIFIED until visually audited: {pupil_hits} success images saved to {AUDIT_DIR}")

    if len(valid) < 2:
        print("Too few valid detections to plot a meaningful trajectory.")
        return

    t0 = rows[0]["t"]
    times = [r["t"] - t0 for r in valid]
    xs = [r["x"] for r in valid]
    ys = [r["y"] for r in valid]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(times, xs, marker='o', linestyle='-', markersize=3)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Relative pupil_x (pixels within eye ROI)")
    ax.set_title("Relative pupil position over time (NOT absolute gaze coordinates) -- UNVERIFIED, see audit images")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "pupil_trajectory.png"), dpi=120)
    plt.close(fig)

    color_map = {"LEFT": "red", "CENTER": "green", "RIGHT": "blue", "UP": "orange", "DOWN": "purple"}
    fig2, ax2 = plt.subplots(figsize=(6, 6))
    for t in TARGETS:
        tx = [r["x"] for r in valid if r["target"] == t]
        ty = [r["y"] for r in valid if r["target"] == t]
        ax2.scatter(tx, ty, label=t, color=color_map[t], s=15)
    ax2.set_xlabel("Relative pupil_x")
    ax2.set_ylabel("Relative pupil_y")
    ax2.set_title("Relative pupil position by gaze target -- UNVERIFIED, see audit images")
    ax2.legend()
    ax2.invert_yaxis()
    fig2.tight_layout()
    fig2.savefig(os.path.join(RESULTS_DIR, "pupil_xy_by_target.png"), dpi=120)
    plt.close(fig2)

    print(f"Plots saved to {RESULTS_DIR}")

if __name__ == "__main__":
    main()
