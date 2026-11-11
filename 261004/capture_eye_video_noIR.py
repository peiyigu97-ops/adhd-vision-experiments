"""
7f阶段续：为EllSeg"更大样本量+连续视频流复测"采集的无IR眼部特写序列。

和第五阶段(eye_roi.py)的区别：那边是"按键触发"的离散单帧采集（20张，互相
之间没有时间连续性，只适合测"单帧检出率"，测不出"追踪稳不稳"）。这里改成
"持续记录一段时间内的连续帧"，严格保留时间顺序和真实时间戳，这样才能把
这批帧按顺序喂给EllSeg，检验瞳孔坐标从一帧到下一帧有没有突变/跳变——
这是静态单帧测试回答不了的问题，也是7f.8节明确列的下一步。

复用eye_roi.py已验证过的Haar cascade自动ROI检测逻辑，检测算法本身没有改动。

已知限制（如实说明，不是缺陷）：
  - 只保存"确实检测到眼部ROI"的那些帧，检测不到的帧直接跳过不保存——
    保存下来的序列在时间戳上因此不是严格等间隔的（中间有检测失败被跳过
    的帧）。脚本结束时会如实报告ROI命中率，暴露跳帧比例，不假装序列是
    无缝连续的。
  - 沿用第三阶段"PNG无损格式"的决定（避免JPEG压缩伪影污染后续瞳孔边界
    像素级精度），所以采集时长故意限制在一个可控范围内（默认20秒），
    不是录不了更久，是避免一次产生几百上千个文件。

Camera index不是永久常量，上次(10/9)验证的值是0，这次插拔过USB的话不保证
还对——不确定就先跑identify_camera.py核实一遍，不要凭上次结论假设。

Usage:
    python capture_eye_video_noIR.py
    python capture_eye_video_noIR.py --duration 30 --camera-index 1
    (运行中按q可随时提前结束)
"""
import argparse
import os
import time

import cv2

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "data", "eye_video_noIR")
os.makedirs(OUT_DIR, exist_ok=True)

WIDTH, HEIGHT = 1280, 720

# 不能用脚本自己所在目录(_CASCADE_DIR = BASE)来加载这两个XML -- 本项目目录
# 现在整个搬到了"作品集\课程"这个含中文字符的路径下，OpenCV的CascadeClassifier
# 底层C++ FileStorage读取函数打不开非ASCII路径(报告第1.3节记录过的老问题，
# 因为后续项目目录重新归档整理搬进了中文路径，这个问题又复发了)。改成从
# D:\cv_cascades\这个纯ASCII路径加载(已用copy_cascades逻辑手动复制过一份)。
_CASCADE_DIR = r"D:\cv_cascades"
face_cascade = cv2.CascadeClassifier(os.path.join(_CASCADE_DIR, "haarcascade_frontalface_default.xml"))
eye_cascade = cv2.CascadeClassifier(os.path.join(_CASCADE_DIR, "haarcascade_eye.xml"))


def imwrite_unicode(path, img):
    """cv2.imwrite在含中文字符的Windows路径下会静默失败(见261004第7d.2节
    踩过的坑：D:\\...\\作品集\\课程\\...)，改用encode+tofile绕开，这是本项目
    涉及图像读写的脚本统一遵循的模式。"""
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def detect_eye(gray_frame):
    """与eye_roi.py完全相同的检测逻辑：先找脸缩小范围，再在脸内找眼睛。"""
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    if len(faces) == 0:
        return None
    fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray_frame[fy:fy + fh, fx:fx + fw]
    eyes = eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=8, minSize=(20, 20))
    if len(eyes) == 0:
        return None
    ex, ey, ew, eh = max(eyes, key=lambda e: e[2] * e[3])
    return (fx + ex, fy + ey, ew, eh)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=20.0, help="采集时长(秒)，默认20")
    parser.add_argument("--camera-index", type=int, default=0,
                         help="摄像头index，默认0(上次10/9验证值，不保证现在仍对)")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"打不开摄像头 index={args.camera_index}——先确认接线，或先跑identify_camera.py核实index")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    print(f"开始连续采集 {args.duration:.0f} 秒，检测到眼部ROI的帧才会保存。")
    print("采集期间请保持正常睁眼、可以自然转动视线（这正是要测的场景），按q可提前结束。\n")

    seq = 0
    total_frames = 0
    roi_hits = 0
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
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            roi = detect_eye(gray)
            display = frame.copy()

            if roi is not None:
                roi_hits += 1
                x, y, w, h = roi
                cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
                eye_crop = gray[y:y + h, x:x + w]
                ts_ms = int(time.time() * 1000)
                fname = os.path.join(OUT_DIR, f"frame_{seq:05d}_{ts_ms}.png")
                if imwrite_unicode(fname, eye_crop):
                    seq += 1
                else:
                    print(f"  警告: 第{total_frames}帧写盘失败，跳过未计入已保存序列: {fname}")
            else:
                cv2.putText(display, "no eye ROI this frame (skipped, not saved)",
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            hit_rate = 100.0 * roi_hits / total_frames if total_frames else 0
            measured_fps = total_frames / elapsed if elapsed > 0 else 0
            cv2.putText(display,
                        f"t={elapsed:.1f}/{args.duration:.0f}s  saved={seq}  "
                        f"ROI hit rate={hit_rate:.1f}%  measured FPS={measured_fps:.1f}",
                        (20, HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            cv2.imshow("capture_eye_video_noIR (q to stop early)", display)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        # Ctrl+C中断也要走到下面的清理+统计打印，不能让已经拍好的帧的
        # 统计信息随着异常一起消失——文件本身已经逐帧落盘了，不受影响，
        # 这里只是确保摄像头资源释放干净、用户能看到最终统计数字。
        print("\n检测到中断(Ctrl+C)，正在清理并汇总已采集的数据...")

    cap.release()
    cv2.destroyAllWindows()

    elapsed = time.time() - start
    measured_fps = total_frames / elapsed if elapsed > 0 else 0
    print("\n=== 采集结束 ===")
    print(f"真实耗时: {elapsed:.1f}秒")
    print(f"总读取帧数: {total_frames}  (真实测量帧率: {measured_fps:.1f} FPS，这是读帧速度，不是保存速度)")
    print(f"ROI命中帧数: {roi_hits} ({100.0*roi_hits/max(1,total_frames):.1f}%)  -- 可对照第五阶段15.5%这个历史数字")
    print(f"实际保存的眼部裁剪序列: {seq} 帧，存到: {OUT_DIR}")
    print("\n这批帧严格按时间顺序命名(frame_00000, 00001, ...)，可以直接喂给EllSeg做连续帧稳定性测试。")


if __name__ == "__main__":
    main()
