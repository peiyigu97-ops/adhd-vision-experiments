"""
STEP 10 (EllSeg version): 5-point gaze calibration, using the validated
EllSeg detector instead of the classical Otsu pipeline.

Why this exists as a separate file from calibration.py (not an edit to it):
calibration.py's original run never produced usable data -- the Otsu
detector it depends on measured 0/20 real success without IR (Stage 6), so
calibration.py's own documented failure mode ("fewer than 3 points have
valid pupil detections") was the expected, inevitable outcome, not a bug.
EllSeg (experiment_report.md 7f/7g) has since been visually audited at
~86% accuracy on the same no-IR hardware, on two independent datasets
(static crops and a separately-captured continuous video). This script
swaps in pupil_detector_ellseg (same detect_pupil() call interface, see
that module's docstring) so calibration has a detector actually worth
running it with. calibration.py is kept as-is, not overwritten, matching
this project's established practice of keeping prior detector variants
side by side (pupil_detector_starburst.py next to pupil_detector.py, etc.)

Also fixes a gap that Stage 9's gaze_experiment.py identified and patched
in itself, but that the original calibration.py never got: a live "Eye ROI"
preview window. Without it, the operator has no way to tell in real time
whether the camera is even pointed at the eye during a hold period --
exactly the issue gaze_experiment.py's 2026-10-09 changelog describes
fixing for itself. Added here from the start.

Known cost, stated plainly (see pupil_detector_ellseg.py docstring and
experiment_report.md 7g.4): EllSeg runs at ~7.8 FPS on this machine's CPU,
not the 60-100+ FPS the Otsu path could attempt. A 2.5s hold period
therefore yields on the order of ~18-20 samples per point, not hundreds.
This is treated as an acceptable trade (few reliable samples > many
~0%-reliable ones), consistent with how 7f/7g concluded EllSeg should
replace the Otsu detector as the primary no-IR pipeline.

Every successful per-frame detection's annotated crop is saved for visual
audit (same practice as gaze_experiment.py's audit image saving) -- a
printed success count must never be trusted on its own, per this project's
repeated finding (Stage 6's original 10% figure, 7a.4's 22% figure, 7f/7g's
100% program-reported figures) that program-reported numbers need visual
confirmation before being treated as real.

Usage:
    python calibration_ellseg.py [--camera-index 1] [--hold-seconds 3.0]
    (camera index is NOT assumed correct -- re-verify with identify_camera.py
    if this machine's USB topology has changed since the last confirmed value)
"""
import argparse
import csv
import os
import time

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from pupil_detector_ellseg import detect_eye, detect_pupil

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE, "data", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

WIDTH, HEIGHT = 1280, 720
# 每次运行独立加时间戳，不用固定文件名 -- 之前固定文件名导致连续几次
# 运行互相覆盖，前三次的原始坐标数据丢失，只剩终端打印的样本数可查。
_RUN_TAG = time.strftime("%Y%m%d_%H%M%S")
CSV_PATH = os.path.join(RESULTS_DIR, f"calibration_ellseg_{_RUN_TAG}.csv")
AUDIT_DIR = os.path.join(RESULTS_DIR, f"calibration_ellseg_audit_{_RUN_TAG}")
os.makedirs(AUDIT_DIR, exist_ok=True)

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
    """Same as calibration.py: 2x3 affine via least squares, screen = A @ [px,py,1]."""
    n = len(pupil_pts)
    if n < 3:
        return None
    ones = np.ones((n, 1))
    X = np.hstack([pupil_pts, ones])
    A = np.zeros((2, 3))
    for dim in range(2):
        y = screen_pts[:, dim]
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        A[dim, :] = coeffs
    return A


def robust_point_estimate(name, samples):
    """
    用中位数+MAD(median absolute deviation)剔除异常样本，再取均值，代替
    之前直接对全部样本取均值的做法。

    动机(7h.5节实测现象)：单点样本量本来就少(3-20个)，个别检测噪声很大
    的样本(例如某次TOP_LEFT只有5个样本，std却高达26px)会把整点的均值
    拖偏很多，直接影响最终标定误差。中位数对这类离群点不敏感，用它先
    定位"大致中心"，再剔除偏离中心过远(>3倍MAD)的样本，比直接均值更稳健。

    样本数<4时直接返回中位数，不做剔除——样本太少时，剔除操作本身可能
    比它要解决的问题更不稳定(有效样本可能被剔到少于3个，无法拟合仿射)。
    """
    arr = np.array(samples)
    n = len(arr)

    if n < 4:
        est = (float(np.median(arr[:, 0])), float(np.median(arr[:, 1])))
        print(f"    {name}: 样本数{n}太少，不做异常值剔除，直接用中位数 -> ({est[0]:.1f},{est[1]:.1f})")
        return est

    med = np.median(arr, axis=0)
    mad = np.median(np.abs(arr - med), axis=0)
    mad_safe = np.where(mad < 1e-6, 1e-6, mad)  # 避免全部样本完全相同时除零

    dist_in_mads = np.abs(arr - med) / mad_safe
    keep_mask = np.all(dist_in_mads <= 3.0, axis=1)
    n_kept = int(keep_mask.sum())

    if n_kept < 3:
        # 剔除后样本太少，退回全量中位数，不强行剔除
        est = (float(np.median(arr[:, 0])), float(np.median(arr[:, 1])))
        print(f"    {name}: 剔除后样本不足3个，退回全量中位数 -> ({est[0]:.1f},{est[1]:.1f})")
        return est

    clean = arr[keep_mask]
    est = (float(np.mean(clean[:, 0])), float(np.mean(clean[:, 1])))
    n_removed = n - n_kept
    if n_removed > 0:
        print(f"    {name}: 剔除{n_removed}个异常样本(共{n}个)，剩余{n_kept}个的均值 -> ({est[0]:.1f},{est[1]:.1f})")
    else:
        print(f"    {name}: 无异常样本，全部{n}个的均值 -> ({est[0]:.1f},{est[1]:.1f})")
    return est


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-index", type=int, default=1,
                         help="摄像头index，默认1(7g.2节最后一次验证值，不保证现在仍对，"
                              "不确定先跑identify_camera.py核实)")
    parser.add_argument("--hold-seconds", type=float, default=3.0,
                         help="每个标定点的停留时长(秒)，默认3.0 -- EllSeg约7.8FPS，"
                              "3秒约产出18-20个有效样本")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"打不开摄像头 index={args.camera_index} -- 先确认接线，或先跑identify_camera.py核实index")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    csv_file = open(CSV_PATH, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow(["timestamp", "point_name", "screen_x", "screen_y",
                      "roi_found", "pupil_x", "pupil_y", "pupil_x_local", "pupil_y_local",
                      "confidence", "audit_image"])

    cv2.namedWindow("Calibration Target", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Calibration Target", CUE_WIDTH, CUE_HEIGHT)

    per_point_samples = {name: [] for name in CALIB_POINTS}
    roi_hits_total = 0
    pupil_hits_total = 0
    frames_total = 0

    print(f"开始5点标定(EllSeg检测器)，每点停留{args.hold_seconds:.1f}秒。")
    print("盯着每个绿色圆点看，同时留意'Eye ROI'窗口确认摄像头真的在追踪你的眼睛。")
    print(f"每次成功检测都会存一张标注图到 {AUDIT_DIR}，供事后肉眼复核。\n")

    for name, (sx, sy) in CALIB_POINTS.items():
        print(f"  标定点: {name} -> 屏幕坐标({sx},{sy})")
        start = time.time()
        point_frame_idx = 0
        while time.time() - start < args.hold_seconds:
            cue_img = np.zeros((CUE_HEIGHT, CUE_WIDTH, 3), dtype=np.uint8)
            cv2.circle(cue_img, (sx, sy), 20, (0, 255, 0), -1)
            cv2.imshow("Calibration Target", cue_img)

            ret, frame = cap.read()
            if not ret:
                cv2.waitKey(1)
                continue
            frames_total += 1
            point_frame_idx += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            ts = time.time()

            pupil_x_local, pupil_y_local, conf = float("nan"), float("nan"), 0.0
            pupil_x, pupil_y = float("nan"), float("nan")  # 全局(摄像头画面固定坐标系)坐标，用于标定拟合
            audit_fname = ""
            roi = detect_eye(gray)
            roi_found = roi is not None

            if roi is not None:
                roi_hits_total += 1
                x, y, w, h = roi
                eye_gray = gray[y:y + h, x:x + w]
                pres = detect_pupil(eye_gray)

                eye_vis = cv2.cvtColor(eye_gray, cv2.COLOR_GRAY2BGR)
                if pres["success"]:
                    pupil_hits_total += 1
                    pupil_x_local, pupil_y_local, conf = pres["pupil_cx"], pres["pupil_cy"], pres["confidence"]
                    # 关键修正：Haar cascade每帧重新检测的裁剪框本身会漂移/缩放，
                    # 如果只记录瞳孔在裁剪框内的局部坐标，检测框的漂移会和瞳孔
                    # 真实的眼球转动互相抵消，吃掉标定需要的方向信号(实测现象：
                    # 头和摄像头都固定不动、只转眼球，仍测不出上下左右的差异)。
                    # 加回裁剪框的偏移量(x,y)，换成摄像头整个固定画面里的绝对坐标，
                    # 这样才能反映眼球相对摄像头的真实转动量。
                    pupil_x = x + pupil_x_local
                    pupil_y = y + pupil_y_local
                    per_point_samples[name].append((pupil_x, pupil_y))
                    # EllSeg有ellipse但没有contour(见pupil_detector_ellseg.py docstring)，
                    # 只画椭圆，不画轮廓
                    cv2.ellipse(eye_vis, pres["ellipse"], (0, 255, 0), 1)
                    cx, cy = int(pupil_x_local), int(pupil_y_local)
                    cv2.circle(eye_vis, (cx, cy), 2, (0, 0, 255), -1)

                    audit_fname = f"{name}_{point_frame_idx}_{int(ts*1000)}.png"
                    ok, buf = cv2.imencode(".png", eye_vis)
                    if ok:
                        buf.tofile(os.path.join(AUDIT_DIR, audit_fname))
                else:
                    cv2.putText(eye_vis, "pupil not found", (3, 15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                cv2.imshow("Eye ROI", eye_vis)
            else:
                blank = np.zeros((100, 100, 3), dtype=np.uint8)
                cv2.putText(blank, "NO EYE", (5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                cv2.imshow("Eye ROI", blank)

            cv2.waitKey(1)
            writer.writerow([f"{ts:.3f}", name, sx, sy, roi_found, pupil_x, pupil_y,
                              pupil_x_local, pupil_y_local, conf, audit_fname])

        n_valid = len(per_point_samples[name])
        print(f"    该点有效样本数: {n_valid}")

    cap.release()
    cv2.destroyAllWindows()
    csv_file.close()

    print(f"\n=== 采集结束 ===")
    print(f"总帧数: {frames_total}")
    print(f"Eye-ROI命中率: {100.0*roi_hits_total/max(1,frames_total):.1f}% ({roi_hits_total}/{frames_total})")
    print(f"瞳孔检出率(给定ROI): {100.0*pupil_hits_total/max(1,roi_hits_total):.1f}% ({pupil_hits_total}/{roi_hits_total})")
    print(f"未经视觉复核: {pupil_hits_total}张成功检测的标注图已存到 {AUDIT_DIR}")

    print("\n--- 各标定点有效样本数 ---")
    pupil_means = {}
    for name, samples in per_point_samples.items():
        print(f"  {name}: {len(samples)} 个有效样本")
        if samples:
            pupil_means[name] = robust_point_estimate(name, samples)

    usable_points = [name for name in CALIB_POINTS if name in pupil_means]
    print(f"\n{len(usable_points)}/5 个点有可用瞳孔数据。")

    if len(usable_points) < 3:
        print("\n标定失败：少于3个点有有效瞳孔检测，无法拟合2D仿射变换。")
        print("如果这个结果和7f/7g节测出的~86%准确率明显不符，先去看audit图片，")
        print("确认到底是真的检测失败、还是头部位置/光照条件和之前测试时差异太大。")
        return

    pupil_pts = np.array([pupil_means[n] for n in usable_points])
    screen_pts = np.array([CALIB_POINTS[n] for n in usable_points])

    A = fit_affine(pupil_pts, screen_pts)
    predicted = np.hstack([pupil_pts, np.ones((len(pupil_pts), 1))]) @ A.T
    errors = np.linalg.norm(predicted - screen_pts, axis=1)
    mean_error = float(np.mean(errors))

    print(f"\n用{len(usable_points)}个点拟合了仿射变换。")
    print(f"各点预测误差(像素): {dict(zip(usable_points, np.round(errors, 1)))}")
    print(f"平均标定误差: {mean_error:.1f} 像素")
    print("\n注意：这个误差是用同一批5个点既拟合又评估得出的(可行性检查)，")
    print("不是独立测试集上的误差，报告时不能过度包装这个数字的含义。")

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(screen_pts[:, 0], screen_pts[:, 1], color="green", s=100, label="Target", marker="o")
    ax.scatter(predicted[:, 0], predicted[:, 1], color="red", s=100, label="Predicted", marker="x")
    for i, name in enumerate(usable_points):
        ax.annotate(name, (screen_pts[i, 0], screen_pts[i, 1]))
    ax.set_xlabel("Screen X (pixels)")
    ax.set_ylabel("Screen Y (pixels)")
    ax.set_title(f"EllSeg calibration (mean error: {mean_error:.1f} px, {len(usable_points)}/5 points)")
    ax.invert_yaxis()
    ax.legend()
    fig.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, f"calibration_ellseg_result_{_RUN_TAG}.png")
    fig.savefig(plot_path, dpi=120)
    plt.close(fig)
    print(f"\n图已存到 {plot_path}")


if __name__ == "__main__":
    main()
