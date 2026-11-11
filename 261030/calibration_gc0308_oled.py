"""
GC0308 -> OLED(128x64) 5点标定，Phase1专用（见261030/README.md）。

和`261004/calibration_ellseg.py`的关键差异：
  1. 标定目标空间是OLED真实像素坐标(128x64)，不是任意的800x600窗口——省掉
     "标定到任意空间后再换算成OLED坐标"这一步换算，这次标定出来的矩阵可以
     直接喂给phase1_fusion.py发/mask请求，不用再转一次。
  2. 不用Haar cascade找眼睛。GC0308近距离工作，眼睛本来就占满画面，正确
     做法是开场手动框一次ROI（复用`261029/gc0308_capture_video.py`验证过的
     做法），固定裁剪框，只调用EllSeg的detect_pupil()，不调用依赖Haar
     cascade的detect_eye()——后者是给OV9281那种"先从大画面里找脸再找眼睛"
     的场景设计的，喂给GC0308的近距离特写大概率找不到"脸"。
  3. 标定完会把仿射矩阵+裁剪框+camera index存成JSON，供phase1_fusion.py
     直接加载复用，不用每次运行都重新标定一遍。

复用`261004/calibration_ellseg.py`的方法论：每点停留若干秒收集多帧样本，
用中位数+MAD剔除异常样本后取均值（这里直接复制了robust_point_estimate()
的逻辑，没有改动，避免两份文件的标定稳健性不一致）。

Usage:
    python calibration_gc0308_oled.py --camera-index 1
    (camera index不保证和上次一样，不确定先跑gc0308/identify_gc0308.py核实)
"""
import argparse
import csv
import json
import os
import sys
import time

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# pupil_detector_ellseg.py里只要detect_pupil()，不要detect_eye()（后者依赖
# Haar cascade，是给OV9281设计的两级检测，GC0308这边用不上，见本文件docstring）。
# 用sys.path把261004加进来直接import，复用EllSeg模型加载那部分代码，不重写
# 一遍（模型加载本身不便宜，这个模块本来就设计成"import一次、全程复用"）。
_PROJ_261004 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "261004"))
sys.path.insert(0, _PROJ_261004)
from pupil_detector_ellseg import detect_pupil  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE, "data", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)
CALIB_JSON_PATH = os.path.join(BASE, "gc0308_oled_calibration.json")

CAM_WIDTH, CAM_HEIGHT = 640, 480  # 同gc0308_capture_video.py的采集分辨率

# ---- 标定目标：OLED真实坐标系(128x64) ----
OLED_W, OLED_H = 128, 64
OLED_MARGIN = 14  # 四角点离边缘留一点余量，避免贴死边框
CALIB_POINTS_OLED = {
    "TOP_LEFT": (OLED_MARGIN, OLED_MARGIN),
    "TOP_RIGHT": (OLED_W - OLED_MARGIN, OLED_MARGIN),
    "CENTER": (OLED_W // 2, OLED_H // 2),
    "BOTTOM_LEFT": (OLED_MARGIN, OLED_H - OLED_MARGIN),
    "BOTTOM_RIGHT": (OLED_W - OLED_MARGIN, OLED_H - OLED_MARGIN),
}
# 标定时在PC屏幕上把OLED坐标系放大显示，不然128x64的窗口小到看不清目标点
# 在哪——放大倍数只影响"人眼怎么看标定点"，不影响实际记录/拟合用的坐标，
# 那些坐标全程都是OLED原始的128x64空间。
DISPLAY_SCALE = 8


def fit_affine(pupil_pts, oled_pts):
    """同calibration_ellseg.py: 2x3仿射，oled = A @ [px,py,1]."""
    n = len(pupil_pts)
    if n < 3:
        return None
    ones = np.ones((n, 1))
    X = np.hstack([pupil_pts, ones])
    A = np.zeros((2, 3))
    for dim in range(2):
        y = oled_pts[:, dim]
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        A[dim, :] = coeffs
    return A


def robust_point_estimate(name, samples):
    """逐字复用calibration_ellseg.py 7h.5节验证过的剔除异常值方法，不改逻辑，
    避免两份标定脚本的稳健性行为不一致。"""
    arr = np.array(samples)
    n = len(arr)

    if n < 4:
        est = (float(np.median(arr[:, 0])), float(np.median(arr[:, 1])))
        print(f"    {name}: 样本数{n}太少，不做异常值剔除，直接用中位数 -> ({est[0]:.1f},{est[1]:.1f})")
        return est

    med = np.median(arr, axis=0)
    mad = np.median(np.abs(arr - med), axis=0)
    mad_safe = np.where(mad < 1e-6, 1e-6, mad)

    dist_in_mads = np.abs(arr - med) / mad_safe
    keep_mask = np.all(dist_in_mads <= 3.0, axis=1)
    n_kept = int(keep_mask.sum())

    if n_kept < 3:
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
                         help="GC0308的camera index，默认1(上次验证值，不保证现在仍对，"
                              "不确定先跑gc0308/identify_gc0308.py核实)")
    parser.add_argument("--hold-seconds", type=float, default=3.0,
                         help="每个标定点的停留时长(秒)，默认3.0")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"打不开摄像头 index={args.camera_index} -- 先跑 gc0308/identify_gc0308.py 核实index")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    for _ in range(10):
        cap.read()  # warm up

    print("把GC0308对准眼睛(固定安装的那套)。")
    print("即将弹出一个窗口 -- 拖一个紧贴眼睛的框，排除鼻梁/眼下容易出噪点的区域")
    print("(和gc0308_capture_video.py/gc0308_pupil_test_cropped.py同一套做法)。")
    print("框选完按ENTER/SPACE确认。\n")

    ret, frame = cap.read()
    if not ret:
        print("读取初始帧失败。")
        return
    roi = cv2.selectROI("Select eye region (exclude nose bridge)", frame, showCrosshair=True)
    cv2.destroyWindow("Select eye region (exclude nose bridge)")
    rx, ry, rw, rh = roi
    if rw == 0 or rh == 0:
        print("没有选中ROI，退出。")
        return
    print(f"固定裁剪框: x={rx}, y={ry}, w={rw}, h={rh}\n")

    _RUN_TAG = time.strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(RESULTS_DIR, f"calibration_gc0308_oled_{_RUN_TAG}.csv")
    audit_dir = os.path.join(RESULTS_DIR, f"calibration_gc0308_oled_audit_{_RUN_TAG}")
    os.makedirs(audit_dir, exist_ok=True)
    csv_file = open(csv_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    writer.writerow(["timestamp", "point_name", "oled_x", "oled_y",
                      "pupil_x_crop", "pupil_y_crop", "confidence", "audit_image"])

    cv2.namedWindow("Calibration Target (scaled, real coords are OLED 128x64)", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Calibration Target (scaled, real coords are OLED 128x64)",
                      OLED_W * DISPLAY_SCALE, OLED_H * DISPLAY_SCALE)

    per_point_samples = {name: [] for name in CALIB_POINTS_OLED}
    pupil_hits_total = 0
    frames_total = 0

    print(f"开始5点标定，每点停留{args.hold_seconds:.1f}秒，目标坐标就是OLED真实像素(128x64)。")
    print(f"每次成功检测都会存一张标注图到 {audit_dir}，供事后肉眼复核。\n")

    for name, (ox, oy) in CALIB_POINTS_OLED.items():
        print(f"  标定点: {name} -> OLED坐标({ox},{oy})")
        start = time.time()
        point_frame_idx = 0
        while time.time() - start < args.hold_seconds:
            cue_img = np.zeros((OLED_H * DISPLAY_SCALE, OLED_W * DISPLAY_SCALE, 3), dtype=np.uint8)
            cv2.circle(cue_img, (ox * DISPLAY_SCALE, oy * DISPLAY_SCALE), 10 * DISPLAY_SCALE // 8,
                       (0, 255, 0), -1)
            cv2.imshow("Calibration Target (scaled, real coords are OLED 128x64)", cue_img)

            ret, frame = cap.read()
            if not ret:
                cv2.waitKey(1)
                continue
            frames_total += 1
            point_frame_idx += 1
            gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
            crop = gray_full[ry:ry + rh, rx:rx + rw]
            ts = time.time()

            pres = detect_pupil(crop)
            vis = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
            audit_fname = ""
            pupil_x_crop, pupil_y_crop, conf = float("nan"), float("nan"), 0.0

            if pres["success"]:
                pupil_hits_total += 1
                pupil_x_crop, pupil_y_crop, conf = pres["pupil_cx"], pres["pupil_cy"], pres["confidence"]
                per_point_samples[name].append((pupil_x_crop, pupil_y_crop))
                cv2.ellipse(vis, pres["ellipse"], (0, 255, 0), 1)
                cv2.circle(vis, (int(pupil_x_crop), int(pupil_y_crop)), 2, (0, 0, 255), -1)
                audit_fname = f"{name}_{point_frame_idx}_{int(ts*1000)}.png"
                ok, buf = cv2.imencode(".png", vis)
                if ok:
                    buf.tofile(os.path.join(audit_dir, audit_fname))
            else:
                cv2.putText(vis, "pupil not found", (3, 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            cv2.imshow("GC0308 crop (fixed ROI)", vis)

            cv2.waitKey(1)
            writer.writerow([f"{ts:.3f}", name, ox, oy, pupil_x_crop, pupil_y_crop, conf, audit_fname])

        n_valid = len(per_point_samples[name])
        print(f"    该点有效样本数: {n_valid}")

    cap.release()
    cv2.destroyAllWindows()
    csv_file.close()

    print("\n=== 采集结束 ===")
    print(f"总帧数: {frames_total}")
    print(f"瞳孔检出率: {100.0*pupil_hits_total/max(1,frames_total):.1f}% ({pupil_hits_total}/{frames_total}) "
          f"-- 程序原始数字，未经视觉复核")
    print(f"未经视觉复核: 成功检测的标注图已存到 {audit_dir}")

    print("\n--- 各标定点有效样本数 ---")
    pupil_means = {}
    for name, samples in per_point_samples.items():
        print(f"  {name}: {len(samples)} 个有效样本")
        if samples:
            pupil_means[name] = robust_point_estimate(name, samples)

    usable_points = [name for name in CALIB_POINTS_OLED if name in pupil_means]
    print(f"\n{len(usable_points)}/5 个点有可用瞳孔数据。")

    if len(usable_points) < 3:
        print("\n标定失败：少于3个点有有效瞳孔检测，无法拟合2D仿射变换，不会写出calibration JSON。")
        print("先去audit_dir看标注图，确认是真的检测失败还是摄像头没对准/裁剪框选错了。")
        csv_file.close()
        return

    pupil_pts = np.array([pupil_means[n] for n in usable_points])
    oled_pts = np.array([CALIB_POINTS_OLED[n] for n in usable_points])

    A = fit_affine(pupil_pts, oled_pts)
    predicted = np.hstack([pupil_pts, np.ones((len(pupil_pts), 1))]) @ A.T
    errors = np.linalg.norm(predicted - oled_pts, axis=1)
    mean_error = float(np.mean(errors))

    print(f"\n用{len(usable_points)}个点拟合了仿射变换。")
    print(f"各点预测误差(OLED像素): {dict(zip(usable_points, np.round(errors, 1)))}")
    print(f"平均标定误差: {mean_error:.1f} 个OLED像素 (OLED总宽128、总高64，这个误差占比"
          f"多大一眼就能看出来，不需要再换算)")
    print("\n注意：这个误差是用同一批5个点既拟合又评估得出的(可行性检查)，")
    print("不是独立测试集上的误差，报告时不能过度包装这个数字的含义。")

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(oled_pts[:, 0], oled_pts[:, 1], color="green", s=100, label="Target (OLED px)", marker="o")
    ax.scatter(predicted[:, 0], predicted[:, 1], color="red", s=100, label="Predicted", marker="x")
    for i, name in enumerate(usable_points):
        ax.annotate(name, (oled_pts[i, 0], oled_pts[i, 1]))
    ax.set_xlim(-10, OLED_W + 10)
    ax.set_ylim(-10, OLED_H + 10)
    ax.set_xlabel("OLED X (pixels, 0-128)")
    ax.set_ylabel("OLED Y (pixels, 0-64)")
    ax.set_title(f"GC0308->OLED calibration (mean error: {mean_error:.1f}px, {len(usable_points)}/5 points)")
    ax.invert_yaxis()
    ax.legend()
    fig.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, f"calibration_gc0308_oled_result_{_RUN_TAG}.png")
    fig.savefig(plot_path, dpi=120)
    plt.close(fig)
    print(f"图已存到 {plot_path}")

    # --- 写出给phase1_fusion.py直接加载的标定文件 ---
    calib_data = {
        "camera_index": args.camera_index,
        "crop_roi": {"x": int(rx), "y": int(ry), "w": int(rw), "h": int(rh)},
        "affine_matrix": A.tolist(),  # oled = A @ [pupil_x_crop, pupil_y_crop, 1]
        "mean_error_px": mean_error,
        "usable_points": usable_points,
        "run_tag": _RUN_TAG,
    }
    with open(CALIB_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(calib_data, f, ensure_ascii=False, indent=2)
    print(f"\n标定结果已写入 {CALIB_JSON_PATH}，phase1_fusion.py会直接加载这个文件，"
          f"不用每次重新标定。如果GC0308的物理位置以后又变了，重新跑一遍本脚本覆盖它。")


if __name__ == "__main__":
    main()
