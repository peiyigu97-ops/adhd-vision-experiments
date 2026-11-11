"""
GC0308 continuous-video capture -- see experiment_report.md 7i.7 (next step
after the 62/62 static-crop audit came back at ~86.9%, fair-frame口径,
basically matching OV9281+EllSeg). Static crops can't answer "does it stay
stable frame to frame" -- this script exists to get that data, same role
`capture_eye_video_noIR.py` played for OV9281 in 7f.8->7g.

Unlike OV9281's capture script, this one does NOT run Haar cascade per
frame. Per 7b.1/7b.4, GC0308 is used at a fixed close-up working distance
(3-5cm) where the eye already fills most of the frame -- the thing that
needed excluding was NOT "where is the eye in a wide scene", it was the
nose-bridge/under-eye sensor-noise patch next to it (see
gc0308_pupil_test_cropped.py). So this script reuses that script's approach:
one manual cv2.selectROI() crop at the start of the session (module is
fixed-mount now, not hand-held, so the crop should stay valid for the whole
recording), then continuous auto-save for a fixed duration -- no per-frame
ROI re-detection, no key presses needed once recording starts.

Camera index is NOT assumed. Per 7a.2/7b.2/7c.1/7g.2 (OV9281) this value
drifts across USB re-enumerations and must be re-checked every session --
run gc0308/identify_gc0308.py first if unsure, then pass the right index
with --camera-index.

Usage:
    python gc0308_capture_video.py
    python gc0308_capture_video.py --duration 20 --camera-index 1
    (after drawing the crop box and pressing ENTER/SPACE, recording starts
    immediately and runs for --duration seconds; press q to stop early)
"""
import argparse
import os
import time

import cv2

# This script's own folder is 课程/261029/; output data lives under
# 课程/261004/gc0308/ alongside the rest of the GC0308 dataset (same split
# as gc0308_rerun_ellseg.py / 261022, see experiment_report.md 7i.5).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GC0308_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "261004", "gc0308"))
OUT_DIR = os.path.join(GC0308_DIR, "data", "gc0308_video")
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 640, 480  # same capture resolution gc0308_pupil_test_cropped.py used


def imwrite_unicode(path, img):
    """cv2.imwrite silently fails on non-ASCII Windows paths (project tree
    lives under 作品集/课程/...) -- established workaround across this
    project's scripts."""
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=20.0, help="采集时长(秒)，默认20")
    parser.add_argument("--camera-index", type=int, default=1,
                         help="摄像头index，默认1(7b.2节上次验证值，不保证现在仍对——"
                              "不确定就先跑 gc0308/identify_gc0308.py 核实)")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"打不开摄像头 index={args.camera_index} —— 先跑 gc0308/identify_gc0308.py 核实index")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    for _ in range(10):
        cap.read()  # warm up

    print("把模组固定对准眼睛(现在是固定安装，不是手持)。")
    print("即将弹出一个窗口 -- 拖一个紧贴眼睛的框，排除鼻梁/眼下容易出噪点的区域")
    print("(和gc0308_pupil_test_cropped.py同一套做法)。框选完按ENTER/SPACE确认。\n")

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
    print(f"固定裁剪框: x={rx}, y={ry}, w={rw}, h={rh}")
    print(f"\n开始连续采集 {args.duration:.0f} 秒，这段时间内自然转动视线(这正是要测的场景)。")
    print("按q可随时提前结束。\n")

    seq = 0
    total_frames = 0
    start = time.time()

    try:
        while True:
            elapsed = time.time() - start
            if elapsed > args.duration:
                break

            ret, frame = cap.read()
            if not ret:
                continue
            total_frames += 1
            gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
            crop = gray_full[ry:ry + rh, rx:rx + rw]

            ts_ms = int(time.time() * 1000)
            fname = os.path.join(OUT_DIR, f"frame_{seq:05d}_{ts_ms}.png")
            if imwrite_unicode(fname, crop):
                seq += 1
            else:
                print(f"  警告: 第{total_frames}帧写盘失败，跳过: {fname}")

            display = frame.copy()
            cv2.rectangle(display, (rx, ry), (rx + rw, ry + rh), (0, 255, 0), 1)
            measured_fps = total_frames / elapsed if elapsed > 0 else 0
            cv2.putText(display, f"t={elapsed:.1f}/{args.duration:.0f}s  saved={seq}  measured FPS={measured_fps:.1f}",
                        (10, HEIGHT - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            cv2.imshow("GC0308 video capture (q to stop early)", display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        print("\n检测到中断(Ctrl+C)，正在清理并汇总已采集的数据...")

    cap.release()
    cv2.destroyAllWindows()

    elapsed = time.time() - start
    measured_fps = total_frames / elapsed if elapsed > 0 else 0
    print("\n=== 采集结束 ===")
    print(f"真实耗时: {elapsed:.1f}秒")
    print(f"总帧数(读取=保存，因为这次没有ROI检测会失败的情况): {total_frames}")
    print(f"真实测量摄像头读帧速度: {measured_fps:.1f} FPS")
    print(f"固定裁剪框: x={rx}, y={ry}, w={rw}, h={rh}  (写进文件名之外没有单独存，"
          f"如果下一步分析脚本需要，从这行终端输出里抄)")
    print(f"保存位置: {OUT_DIR}")
    print("\n这批帧严格按真实时间戳命名(frame_00000_<ts>, frame_00001_<ts>, ...)，"
          "可以直接喂给gc0308_rerun_ellseg_video.py做连续帧稳定性测试。")


if __name__ == "__main__":
    main()
