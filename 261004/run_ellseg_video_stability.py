"""
7f阶段续：EllSeg在连续视频流上的帧间稳定性分析。

用`capture_eye_video_noIR.py`采集的连续帧序列（data/eye_video_noIR/），按
时间顺序逐帧跑EllSeg，检验瞳孔坐标从一帧到下一帧有没有突变/跳变——这是
之前20张静态图测试（互相没有时间连续性）回答不了的问题，也是7f.8节列的
下一步。

本次采集实际产生了两个独立会话（根据文件名时间戳聚类识别，两次运行之间
有明显时间间隔，不是同一段连续录制）：
  - session A: 约77帧，裁剪尺寸只有约70-80像素（远小于EllSeg期望的320宽度，
    放大后会严重模糊失真），画质明显更差
  - session B: 约265帧，裁剪尺寸约270-350像素，画质更接近之前静态测试用的
    20张样本（216-245像素），是本次分析的主力数据

两个session分开处理、分开报告，不混在一起算一个数字——这和session内部画质
不均匀是两回事：sessionB内部帧间画质應该相对稳定(同一次连续拍摄)，但
sessionA和sessionB之间的画质差异很大，混在一起会让"帧间抖动"这个指标
的含义变得模糊（分不清抖动是真实追踪不稳，还是两个数据源画质差异造成的）。

指标：
  1. 每帧检出率(有多少帧EllSeg给出了非nan的瞳孔中心)
  2. 帧间抖动：连续两帧瞳孔中心的欧氏距离，这是本次新增的指标(静态图
     测试没有"连续两帧"这个概念)。注意：这个距离里既包含"检测噪声导致的
     抖动"，也包含"用户真实在转动视线导致的位置变化"，两者无法从这一个
     数字里拆开——需要结合contact sheet视觉复核才能判断抖动是真实的还是
     噪声。
  3. 实际吞吐：处理这批真实帧的真实墙钟耗时/帧数，而不是之前单帧benchmark
     那个理论上限(126ms/帧，7.9FPS)——这次把图像读取、预处理也算进去，
     看看和理论值差多少。

Usage:
    python run_ellseg_video_stability.py
Outputs:
    data/results/ellseg_video_sessionB_timeline.csv   逐帧结果+帧间距离
    data/results/ellseg_video_sessionB_jitter_plot.png  瞳孔中心轨迹+抖动曲线
    data/results/ellseg_video_sessionB_sample_contact_sheet.png  抽样帧的标注图，供视觉复核
"""
import os
import re
import csv
import glob
import time
from collections import defaultdict

import cv2
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
ELLSEG_DIR = r"C:\Users\34659\AppData\Local\Temp\EllSeg"
sys.path.insert(0, ELLSEG_DIR)
from models.RITnet_v3 import DenseNet2D       # noqa: E402
from utils import get_predictions              # noqa: E402
from loss import get_seg2ptLoss                # noqa: E402
from helperfunctions import plot_segmap_ellpreds  # noqa: E402
from helperfunctions import my_ellipse         # noqa: E402

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = os.path.join(PROJ_DIR, "data", "eye_video_noIR")
RESULTS_DIR = os.path.join(PROJ_DIR, "data", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def imread_unicode(path, flags=cv2.IMREAD_GRAYSCALE):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, flags)


def imwrite_unicode(path, img):
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def group_into_sessions(files):
    """按文件名里嵌入的真实时间戳聚类成独立的录制会话 -- 两次运行之间的
    文件名序号都从0开始，不能靠序号区分，只能靠真实时间戳聚类。"""
    parsed = []
    for f in files:
        m = re.match(r"frame_(\d+)_(\d+)\.png", os.path.basename(f))
        if m:
            parsed.append((int(m.group(1)), int(m.group(2)), f))
    parsed.sort(key=lambda t: t[1])  # 按真实时间戳排序，不是按文件名序号
    sessions = []
    cur = [parsed[0]]
    for item in parsed[1:]:
        if item[1] - cur[-1][1] < 5000:  # 5秒内算同一会话
            cur.append(item)
        else:
            sessions.append(cur)
            cur = [item]
    sessions.append(cur)
    return sessions


def preprocess_frame(img, op_shape=(240, 320)):
    sc = op_shape[1] / img.shape[1]
    # 原来这里用 int(img.shape[1] * sc) 重新算宽度，数学上应该总是等于
    # op_shape[1]，但浮点误差会让某些尺寸的输入算出319.999...，截断成319、
    # 差1像素——这1像素经过模型内部多层下采样会被放大，导致矩阵维度对不上
    # (265帧里5帧真实撞上了这个边界情况)。既然目标宽度本来就是已知的常量，
    # 不需要重新用浮点乘法算一遍，直接用op_shape[1]本身，从根上消除这个误差来源。
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


def run_ellseg_on_session(model, session_files, session_name):
    rows = []
    overlays = []
    t_start = time.time()
    with torch.no_grad():
        for seq_idx, (local_seq, ts, path) in enumerate(session_files):
            img = imread_unicode(path)
            if img is None:
                continue
            t_tensor, sc, pad = preprocess_frame(img)
            x4, x3, x2, x1, x = model.enc(t_tensor)
            elOut = model.elReg(x, 0)
            seg_out = model.dec(x4, x3, x2, x1, x)
            seg_map = get_predictions(seg_out).squeeze().numpy()

            _, norm_pupil_center = get_seg2ptLoss(seg_out[:, 2, ...], torch.zeros(2,), temperature=4)
            H, W = 240, 320
            Hm = np.array([[W/2, 0, W/2], [0, H/2, H/2], [0, 0, 1]])
            elOut_sq = elOut.squeeze()
            norm_pupil_ellipse = torch.cat([norm_pupil_center.squeeze(0), elOut_sq[7:10]])
            pupil_ellipse = my_ellipse(norm_pupil_ellipse.numpy()).transform(Hm)[0][:-1]

            # 还原回原图坐标系(撤销preprocess_frame里的resize+pad)
            pupil_ellipse = np.array(pupil_ellipse, dtype=np.float64)
            pupil_ellipse[1] -= np.floor(pad // 2)
            pupil_ellipse[:-1] /= sc

            found = not np.all(pupil_ellipse == -1) and not np.isnan(pupil_ellipse[:2]).any()
            rows.append({
                "session": session_name, "seq": local_seq, "timestamp_ms": ts,
                "filename": os.path.basename(path),
                "pupil_cx": pupil_ellipse[0] if found else np.nan,
                "pupil_cy": pupil_ellipse[1] if found else np.nan,
                "found": found,
            })

            if seq_idx % 20 == 0:  # 每20帧存一张标注图供抽样视觉复核，不是全部存(265张太多)
                seg_map_orig = cv2.resize(seg_map.astype(np.uint8), (img.shape[1], img.shape[0]),
                                           interpolation=cv2.INTER_NEAREST)
                overlay = plot_segmap_ellpreds(img, seg_map_orig, pupil_ellipse.copy(),
                                                np.array([-1, -1, -1, -1, -1]))
                overlays.append((os.path.basename(path), overlay[..., ::-1].astype(np.uint8)))

    elapsed = time.time() - t_start
    n = len(rows)
    print(f"[{session_name}] {n}帧，真实墙钟耗时{elapsed:.1f}s，"
          f"实测吞吐{n/elapsed:.2f} FPS(含图像读取+预处理+推理+坐标还原全流程)")
    return rows, overlays


def analyze_jitter(rows):
    """计算相邻帧瞳孔中心的欧氏距离，NaN(检测失败)的帧不参与距离计算但
    保留在时间序列里(不能悄悄删掉，否则"前一帧"的定义会错位)。"""
    cx = np.array([r["pupil_cx"] for r in rows])
    cy = np.array([r["pupil_cy"] for r in rows])
    dist = np.full(len(rows), np.nan)
    for i in range(1, len(rows)):
        if not (np.isnan(cx[i]) or np.isnan(cx[i-1])):
            dist[i] = np.hypot(cx[i]-cx[i-1], cy[i]-cy[i-1])
    for i, r in enumerate(rows):
        r["frame_to_frame_dist_px"] = dist[i]
    return rows


def main():
    files = glob.glob(os.path.join(VIDEO_DIR, "*.png"))
    sessions = group_into_sessions(files)
    sessions.sort(key=len, reverse=True)
    print(f"识别到 {len(sessions)} 个录制会话，按帧数从大到小: {[len(s) for s in sessions]}")

    model = DenseNet2D()
    netDict = torch.load(os.path.join(ELLSEG_DIR, "weights", "all.git_ok"), map_location="cpu")
    model.load_state_dict(netDict["state_dict"], strict=True)
    model.eval()

    # 只处理最大的会话(session B, 画质更好的那批)，小的那批裁剪尺寸太小
    # (约70-80px)，放大失真严重，单独跑没有意义，仅在汇总里如实报告跳过原因
    target_session = sessions[0]
    rows, overlays = run_ellseg_on_session(model, target_session, "sessionB")
    rows = analyze_jitter(rows)

    csv_path = os.path.join(RESULTS_DIR, "ellseg_video_sessionB_timeline.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["session", "seq", "timestamp_ms", "filename",
                                                "pupil_cx", "pupil_cy", "found", "frame_to_frame_dist_px"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"写入 {csv_path}")

    n_total = len(rows)
    n_found = sum(1 for r in rows if r["found"])
    dists = np.array([r["frame_to_frame_dist_px"] for r in rows if not np.isnan(r["frame_to_frame_dist_px"])])
    print(f"\n检出率: {n_found}/{n_total} ({100.0*n_found/n_total:.1f}%) -- 程序原始数字，未经视觉复核")
    if len(dists) > 0:
        print(f"帧间瞳孔中心位移: 中位数={np.median(dists):.1f}px, 均值={np.mean(dists):.1f}px, "
              f"最大={np.max(dists):.1f}px, 90分位={np.percentile(dists,90):.1f}px")

    # --- 轨迹+抖动曲线图 ---
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    t = [r["timestamp_ms"] for r in rows]
    t0 = t[0]
    t_sec = [(x - t0)/1000.0 for x in t]
    cx = [r["pupil_cx"] for r in rows]
    cy = [r["pupil_cy"] for r in rows]
    axes[0].plot(t_sec, cx, '.-', label="pupil_cx", markersize=3)
    axes[0].plot(t_sec, cy, '.-', label="pupil_cy", markersize=3)
    axes[0].set_xlabel("time (s)")
    axes[0].set_ylabel("pupil center (px, in crop coords)")
    axes[0].set_title("Session B: pupil center over time (NaN gaps = detection failed that frame)")
    axes[0].legend()

    d = [r["frame_to_frame_dist_px"] for r in rows]
    axes[1].plot(t_sec, d, '.-', color='red', markersize=3)
    axes[1].set_xlabel("time (s)")
    axes[1].set_ylabel("frame-to-frame pupil center shift (px)")
    axes[1].set_title("Frame-to-frame jitter (includes both real gaze movement and detection noise -- "
                       "cannot be separated from this number alone)")
    plt.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, "ellseg_video_sessionB_jitter_plot.png")
    plt.savefig(plot_path, dpi=100)
    print(f"写入 {plot_path}")

    # --- 抽样标注图联系表 ---
    if overlays:
        thumb = 180
        per_row = 5
        n = len(overlays)
        n_rows = (n + per_row - 1) // per_row
        sheet = np.zeros((n_rows*(thumb+25), per_row*thumb, 3), dtype=np.uint8)
        for i, (fname, img_bgr) in enumerate(overlays):
            r, c = divmod(i, per_row)
            resized = cv2.resize(img_bgr, (thumb, thumb), interpolation=cv2.INTER_NEAREST)
            y0, x0 = r*(thumb+25), c*thumb
            sheet[y0:y0+thumb, x0:x0+thumb] = resized
            cv2.putText(sheet, f"#{i*20}", (x0+3, y0+thumb+18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
        sheet_path = os.path.join(RESULTS_DIR, "ellseg_video_sessionB_sample_contact_sheet.png")
        imwrite_unicode(sheet_path, sheet)
        print(f"写入 {sheet_path} (每20帧抽样一张，共{len(overlays)}张，供视觉复核)")

    n_skip = sum(len(s) for s in sessions[1:])
    if n_skip:
        print(f"\n跳过了{n_skip}帧(裁剪尺寸过小的session，约70-80px，放大到320宽度失真严重，不纳入本次分析)")


if __name__ == "__main__":
    main()
