"""
GC0308 continuous-video stability analysis -- see experiment_report.md 7i.7.
Counterpart to run_ellseg_video_stability.py (which did this for OV9281 in
7g), applied to the frames gc0308_capture_video.py just recorded.

Unlike the OV9281 version, there's no Haar-cascade ROI step and no "ROI hit
rate" metric here -- gc0308_capture_video.py already saved pre-cropped eye
frames (one manual crop for the whole session, see that script's docstring
for why that's valid for GC0308's fixed close-up mounting), so every saved
frame is already an eye crop. "found" below means "EllSeg returned a valid
pupil ellipse on this already-cropped frame", not "ROI was located".

Metrics (same three as 7g for OV9281, so the numbers are directly comparable):
  1. per-frame detection rate (program-reported, NOT yet visually audited)
  2. frame-to-frame jitter: Euclidean distance between consecutive frames'
     pupil centers. Mixes real gaze movement and detection noise -- cannot
     be separated from this number alone, same caveat as 7g.5.
  3. real throughput: wall-clock seconds / frame count for the full
     read+preprocess+inference+rescale pipeline, not the single-frame
     theoretical benchmark.

Usage:
    python gc0308_rerun_ellseg_video.py
Outputs (written under 261004/gc0308/data/, not under this script's folder):
    gc0308_results/gc0308_ellseg_video_timeline_<session>.csv       per-frame results + frame-to-frame distance
    gc0308_results/gc0308_ellseg_video_jitter_plot_<session>.png     pupil center trajectory + jitter curve
    gc0308_results/gc0308_ellseg_video_sample_contact_sheet_<session>.png  sampled frames for visual audit

Each output filename is tagged with the session it came from (see
group_into_sessions() below) -- added after this script's first real use
exposed a bug: gc0308_capture_video.py doesn't clear data/gc0308_video/
between runs, so re-recording (e.g. "before vs after rigidly mounting the
module") silently accumulates multiple sessions' frames into one folder.
Before this fix, re-running this script just concatenated both sessions
into one fake continuous timeline and overwrote the previous run's output
files under the same names -- exactly the kind of silent data-merging this
project's methodology elsewhere (7g.2, for OV9281) already flagged as a
trap to avoid.
"""
import argparse
import os
import re
import csv
import glob
import time

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
from loss import get_seg2ptLoss                 # noqa: E402
from helperfunctions import plot_segmap_ellpreds  # noqa: E402
from helperfunctions import my_ellipse          # noqa: E402

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GC0308_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "261004", "gc0308"))
VIDEO_DIR = os.path.join(GC0308_DIR, "data", "gc0308_video")
RESULTS_DIR = os.path.join(GC0308_DIR, "data", "gc0308_results")
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


def load_frames_by_timestamp(files):
    """Sort by the real timestamp embedded in the filename, not by filename
    sequence number -- same rule as run_ellseg_video_stability.py's
    group_into_sessions()."""
    parsed = []
    for f in files:
        m = re.match(r"frame_(\d+)_(\d+)\.png", os.path.basename(f))
        if m:
            parsed.append((int(m.group(1)), int(m.group(2)), f))
    parsed.sort(key=lambda t: t[1])
    return parsed


def group_into_sessions(parsed, gap_ms=5000):
    """Split one sorted (seq, ts, path) list into separate recording
    sessions wherever the real timestamp gap exceeds `gap_ms`.

    This turned out NOT to be a hypothetical case to guard against (as
    originally written) -- it's exactly what happened on the actual re-run
    this function was added for: gc0308_capture_video.py was run twice
    (once handheld, once after the module was rigidly mounted) without
    clearing data/gc0308_video/ in between, so the folder held two distinct
    20-ish-second sessions back to back. Without this split, the analysis
    silently concatenated both into one fake continuous timeline (1032
    frames reported as if they were one recording) -- same mistake
    run_ellseg_video_stability.py's docstring already warned about for
    OV9281's sessionA/sessionB, just not yet wired into this GC0308 copy
    until this bug actually occurred."""
    if not parsed:
        return []
    sessions = [[parsed[0]]]
    for item in parsed[1:]:
        if item[1] - sessions[-1][-1][1] < gap_ms:
            sessions[-1].append(item)
        else:
            sessions.append([item])
    return sessions


def preprocess_frame(img, op_shape=(240, 320)):
    """Identical to run_ellseg_video_stability.py's bugfixed version (7g.3):
    target width must be the op_shape constant directly, not recomputed via
    float multiplication (that recomputation can truncate to 319 instead of
    320 on ~2% of real inputs and crash the model)."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=int, default=-1,
                         help="哪个录制session(按时间先后排，0=最早)。默认-1=最新的一个"
                              "(gc0308_capture_video.py每次运行不清空旧文件，文件夹里可能"
                              "积累了不止一次录制，必须按真实时间戳gap先分开，不能当成一条"
                              "连续时间线直接合并分析)")
    parser.add_argument("--list-sessions", action="store_true", help="只列出识别到的session，不跑推理")
    args = parser.parse_args()

    if not os.path.isdir(VIDEO_DIR):
        raise FileNotFoundError(
            f"Expected GC0308 video frames at {VIDEO_DIR} -- run "
            "gc0308_capture_video.py first (see experiment_report.md 7i.7)."
        )

    files = glob.glob(os.path.join(VIDEO_DIR, "*.png"))
    all_frames = load_frames_by_timestamp(files)
    if not all_frames:
        print(f"No frames found in {VIDEO_DIR}")
        return

    sessions = group_into_sessions(all_frames)
    print(f"识别到 {len(sessions)} 个录制session(按时间戳gap>5秒切分):")
    for i, s in enumerate(sessions):
        span = (s[-1][1] - s[0][1]) / 1000.0
        print(f"  session {i}: {len(s)}帧, 时间跨度{span:.1f}秒, "
              f"起始ts={s[0][1]} ({'最新' if i == len(sessions)-1 else ''})")
    if args.list_sessions:
        return

    frames = sessions[args.session]
    session_label = f"session{args.session if args.session >= 0 else len(sessions) + args.session}"
    print(f"\n本次分析: {session_label} ({len(frames)}帧) —— "
          f"如果这不是你想要的那次录制，用 --session <序号> 或 --list-sessions 重选\n")

    model = DenseNet2D()
    netDict = torch.load(os.path.join(ELLSEG_DIR, "weights", "all.git_ok"), map_location="cpu")
    model.load_state_dict(netDict["state_dict"], strict=True)
    model.eval()

    rows = []
    overlays = []
    t_start = time.time()
    with torch.no_grad():
        for seq_idx, (local_seq, ts, path) in enumerate(frames):
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
            Hm = np.array([[W / 2, 0, W / 2], [0, H / 2, H / 2], [0, 0, 1]])
            elOut_sq = elOut.squeeze()
            norm_pupil_ellipse = torch.cat([norm_pupil_center.squeeze(0), elOut_sq[7:10]])
            pupil_ellipse = my_ellipse(norm_pupil_ellipse.numpy()).transform(Hm)[0][:-1]

            pupil_ellipse = np.array(pupil_ellipse, dtype=np.float64)
            pupil_ellipse[1] -= np.floor(pad // 2)
            pupil_ellipse[:-1] /= sc

            found = not np.all(pupil_ellipse == -1) and not np.isnan(pupil_ellipse[:2]).any()
            rows.append({
                "seq": local_seq, "timestamp_ms": ts, "filename": os.path.basename(path),
                "pupil_cx": pupil_ellipse[0] if found else np.nan,
                "pupil_cy": pupil_ellipse[1] if found else np.nan,
                "found": found,
            })

            if seq_idx % 20 == 0:  # sample every 20th frame for visual audit, not all of them
                seg_map_orig = cv2.resize(seg_map.astype(np.uint8), (img.shape[1], img.shape[0]),
                                           interpolation=cv2.INTER_NEAREST)
                overlay = plot_segmap_ellpreds(img, seg_map_orig, pupil_ellipse.copy(),
                                                np.array([-1, -1, -1, -1, -1]))
                overlays.append((os.path.basename(path), overlay[..., ::-1].astype(np.uint8)))

    elapsed = time.time() - t_start
    n = len(rows)
    print(f"{n}帧，真实墙钟耗时{elapsed:.1f}s，实测吞吐{n/elapsed:.2f} FPS"
          f"(含图像读取+预处理+推理+坐标还原全流程)")

    # --- frame-to-frame jitter ---
    cx = np.array([r["pupil_cx"] for r in rows])
    cy = np.array([r["pupil_cy"] for r in rows])
    dist = np.full(len(rows), np.nan)
    for i in range(1, len(rows)):
        if not (np.isnan(cx[i]) or np.isnan(cx[i - 1])):
            dist[i] = np.hypot(cx[i] - cx[i - 1], cy[i] - cy[i - 1])
    for i, r in enumerate(rows):
        r["frame_to_frame_dist_px"] = dist[i]

    csv_path = os.path.join(RESULTS_DIR, f"gc0308_ellseg_video_timeline_{session_label}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["seq", "timestamp_ms", "filename",
                                                "pupil_cx", "pupil_cy", "found", "frame_to_frame_dist_px"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"写入 {csv_path}")

    n_found = sum(1 for r in rows if r["found"])
    dists = np.array([r["frame_to_frame_dist_px"] for r in rows if not np.isnan(r["frame_to_frame_dist_px"])])
    print(f"\n检出率: {n_found}/{n} ({100.0*n_found/n:.1f}%) -- 程序原始数字，未经视觉复核，"
          f"不能直接拿来和7i.6节62/62静态图86.9%比（统计口径不同，需要视觉复核后才能比）")
    if len(dists) > 0:
        print(f"帧间瞳孔中心位移: 中位数={np.median(dists):.1f}px, 均值={np.mean(dists):.1f}px, "
              f"最大={np.max(dists):.1f}px, 90分位={np.percentile(dists,90):.1f}px "
              f"-- 7g.5节提醒过：这里混了真实视线移动和检测噪声，解读前先核对真实时间间隔"
              f"有没有异常跳变（比如眨眼导致的采集空档）")

    # --- trajectory + jitter plot ---
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    t0 = rows[0]["timestamp_ms"]
    t_sec = [(r["timestamp_ms"] - t0) / 1000.0 for r in rows]
    axes[0].plot(t_sec, [r["pupil_cx"] for r in rows], '.-', label="pupil_cx", markersize=3)
    axes[0].plot(t_sec, [r["pupil_cy"] for r in rows], '.-', label="pupil_cy", markersize=3)
    axes[0].set_xlabel("time (s)")
    axes[0].set_ylabel("pupil center (px, in crop coords)")
    axes[0].set_title("GC0308: pupil center over time (NaN gaps = detection failed that frame)")
    axes[0].legend()

    axes[1].plot(t_sec, [r["frame_to_frame_dist_px"] for r in rows], '.-', color='red', markersize=3)
    axes[1].set_xlabel("time (s)")
    axes[1].set_ylabel("frame-to-frame pupil center shift (px)")
    axes[1].set_title("Frame-to-frame jitter (real gaze movement + detection noise, not separable from this alone)")
    plt.tight_layout()
    plot_path = os.path.join(RESULTS_DIR, f"gc0308_ellseg_video_jitter_plot_{session_label}.png")
    plt.savefig(plot_path, dpi=100)
    print(f"写入 {plot_path}")

    # --- sampled contact sheet for visual audit ---
    if overlays:
        thumb = 180
        per_row = 5
        n_ov = len(overlays)
        n_rows = (n_ov + per_row - 1) // per_row
        sheet = np.zeros((n_rows * (thumb + 25), per_row * thumb, 3), dtype=np.uint8)
        for i, (fname, img_bgr) in enumerate(overlays):
            r, c = divmod(i, per_row)
            resized = cv2.resize(img_bgr, (thumb, thumb), interpolation=cv2.INTER_NEAREST)
            y0, x0 = r * (thumb + 25), c * thumb
            sheet[y0:y0 + thumb, x0:x0 + thumb] = resized
            cv2.putText(sheet, f"#{i*20}", (x0 + 3, y0 + thumb + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        sheet_path = os.path.join(RESULTS_DIR, f"gc0308_ellseg_video_sample_contact_sheet_{session_label}.png")
        imwrite_unicode(sheet_path, sheet)
        print(f"写入 {sheet_path} (每20帧抽样一张，共{len(overlays)}张，供视觉复核)")

    print("\n下一步：和历次一样，程序报告的检出率/位移数字在视觉复核前不采信——"
          "打开contact sheet逐张检查椭圆是否真的套在瞳孔上，再把结论写回experiment_report.md 7i节。")


if __name__ == "__main__":
    main()
