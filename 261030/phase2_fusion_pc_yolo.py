"""
261030 Phase2 (PC端版) -- 真实物体检测替换占位矩形。

背景：讨论Phase2时发现`261003/esp32_camera2_OLED_object_detection.ino`依赖的
Edge Impulse模型("Aida-project-1")根本不是FOMO/目标检测，是个10类整图分类器
（bottle/computer/phone等桌面物品练手项目），见`261022/README.md`"2026-11-04
更正"一节。真要做ESP32本地FOMO检测，需要重新定义类别、采集数据、训练——这是
一块新工作量，不是"接回现成模型"。

讨论后决定：现阶段目标（手机/电脑屏幕/电视）**本来就是COCO数据集的标准类别**，
不需要任何自定义训练，直接用预训练的YOLOv8在PC端跑就能识别，比投入Edge Impulse
训练流程快得多。这是否值得为了延迟换成ESP32本地FOMO，要等这条PC端路径验证过
"实际体验到底需不需要更低延迟"之后再评估——现在还没必要投入训练成本解决一个
未经证实的瓶颈。

和`phase1_fusion.py`的关系：没有覆盖那个文件，新建一份——Phase1的范围定义明确
排除真实物体检测("不碰FOMO")，这个脚本已经不在那个范围内了，按本项目一贯做法
(pupil_detector.py旁边放pupil_detector_starburst.py那种)，新能力用新文件，不
改旧文件的范围定义。

和真正的"Phase2"(261014文档定义：FOMO下放到ESP32本地，PC只发注视点，解决转头
滑移延迟)不是同一件事——这里物体检测仍然在PC端跑，没有解决ESP32本地化/延迟
优化的问题，只是用现成YOLO替换了占位矩形，验证"真实物体检测接入"这条链路，
文件名刻意写成phase2_fusion_pc_yolo而不是phase2_fusion，避免和将来真正的ESP32
本地FOMO方案混淆。

只替换了`phase1_fusion.py`里"干扰物位置"那一半（原来是写死矩形），"真实注视点"
那一半（GC0308+EllSeg+标定矩阵）原样复用，没有改动。

Usage:
    python phase2_fusion_pc_yolo.py --esp32-ip 172.20.10.2 [--target-class "cell phone"]
    (同样需要先跑 calibration_gc0308_oled.py 产出标定JSON)
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

import cv2
import numpy as np
from ultralytics import YOLO

_PROJ_261004 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "261004"))
sys.path.insert(0, _PROJ_261004)
from pupil_detector_ellseg import detect_pupil  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
CALIB_JSON_PATH = os.path.join(BASE, "gc0308_oled_calibration.json")
YOLO_WEIGHTS_PATH = os.path.join(BASE, "yolov8n.pt")

OLED_W, OLED_H = 128, 64
SCENE_W, SCENE_H = 320, 240
SCENE_TO_OLED_SX = OLED_W / SCENE_W
SCENE_TO_OLED_SY = OLED_H / SCENE_H

DISPLAY_SCALE = 4

YOLO_CONF_THRESHOLD = 0.35  # 低于这个置信度的检测直接忽略，不是precision/recall调过的
# 最优值，是一个合理的起点，后续如果误触发/漏检太多，按实际表现调


def scene_rect_to_oled(rect):
    return {
        "x": int(round(rect["x"] * SCENE_TO_OLED_SX)),
        "y": int(round(rect["y"] * SCENE_TO_OLED_SY)),
        "w": int(round(rect["w"] * SCENE_TO_OLED_SX)),
        "h": int(round(rect["h"] * SCENE_TO_OLED_SY)),
    }


def rect_contains(rect, px, py):
    return rect["x"] <= px < rect["x"] + rect["w"] and rect["y"] <= py < rect["y"] + rect["h"]


def http_get(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.URLError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


def send_mask(base_url, rect, on):
    t0 = time.time()
    url = f"{base_url}/mask?x={rect['x']}&y={rect['y']}&w={rect['w']}&h={rect['h']}&on={1 if on else 0}"
    status, body = http_get(url)
    elapsed = time.time() - t0
    tag = "ON " if on else "OFF"
    print(f"  [mask {tag}] {url} -> {status} {body} (耗时{elapsed:.1f}s)")


def fetch_capture(base_url):
    try:
        with urllib.request.urlopen(f"{base_url}/capture", timeout=3) as resp:
            data = resp.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def load_calibration():
    if not os.path.isfile(CALIB_JSON_PATH):
        raise FileNotFoundError(
            f"找不到 {CALIB_JSON_PATH} -- 先跑 calibration_gc0308_oled.py 产出这个文件。"
        )
    with open(CALIB_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"加载标定: camera_index={data['camera_index']}, "
          f"crop_roi={data['crop_roi']}, 标定平均误差={data['mean_error_px']:.1f}px "
          f"(标定于{data['run_tag']})")
    return data


def detect_target(model, scene_img_bgr, target_class_id, conf_threshold):
    """在场景画面上跑YOLO，返回置信度最高的目标检测框(场景像素坐标)，没找到返回None。
    置信度数字直接来自YOLO程序输出，这次没有做本项目一贯的"人工视觉复核"那套流程——
    YOLO是业界广泛验证过的预训练模型，不是本项目自己训练的检测器，不适用
    experiment_report.md里那套"程序输出不可信、必须人工核查"的方法论(那套方法论
    针对的是自己训练/验证中的模型，YOLO是现成的、已经在海量数据上验证过的外部工具)。"""
    results = model.predict(scene_img_bgr, classes=[target_class_id], conf=conf_threshold, verbose=False)
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return None
    confs = boxes.conf.cpu().numpy()
    best_idx = int(np.argmax(confs))
    xyxy = boxes.xyxy.cpu().numpy()[best_idx]
    x1, y1, x2, y2 = xyxy
    return {
        "x": int(x1), "y": int(y1),
        "w": int(x2 - x1), "h": int(y2 - y1),
        "conf": float(confs[best_idx]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--esp32-ip", required=True, help="ESP32CAM的IP地址")
    parser.add_argument("--target-class", default="cell phone",
                         help="要当作干扰物的COCO类别名，默认'cell phone'，"
                              "也可以试'tv'或'laptop'(YOLOv8n的COCO类别名单)")
    args = parser.parse_args()
    base_url = f"http://{args.esp32_ip}"

    print(f"加载YOLO模型: {YOLO_WEIGHTS_PATH}")
    model = YOLO(YOLO_WEIGHTS_PATH)
    name_to_id = {v: k for k, v in model.names.items()}
    if args.target_class not in name_to_id:
        print(f"'{args.target_class}' 不在YOLOv8n的COCO类别里，可用类别举例: "
              f"{list(model.names.values())[:20]} ...")
        return
    target_class_id = name_to_id[args.target_class]
    print(f"目标类别: '{args.target_class}' (class id {target_class_id})，"
          f"置信度阈值 {YOLO_CONF_THRESHOLD}")

    calib = load_calibration()
    cam_index = calib["camera_index"]
    roi = calib["crop_roi"]
    rx, ry, rw, rh = roi["x"], roi["y"], roi["w"], roi["h"]
    A = np.array(calib["affine_matrix"])

    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"打不开GC0308 index={cam_index} -- 物理连接变了的话，重新跑一遍标定脚本")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    for _ in range(10):
        cap.read()

    print("\n这次干扰物位置是真实YOLO检测，不是写死矩形；注视点是真实GC0308+EllSeg数据。")
    print("按q退出(退出前会自动清除OLED，不留卡住的画面)。\n")

    # 三个cv2.imshow窗口默认都开在屏幕左上角同一位置，会完全叠在一起，容易被
    # 误以为"只弹出了一个/两个"——显式指定各窗口位置，错开摆放。
    cv2.namedWindow("GC0308 crop (real-time)")
    cv2.moveWindow("GC0308 crop (real-time)", 50, 50)
    cv2.namedWindow("ESP32CAM scene (real YOLO detection)")
    cv2.moveWindow("ESP32CAM scene (real YOLO detection)", 450, 50)
    cv2.namedWindow("OLED-space (real gaze + real YOLO detection)")
    cv2.moveWindow("OLED-space (real gaze + real YOLO detection)", 850, 50)

    mask_active = False
    last_detect_run = 0.0
    scene_img = None
    current_object_scene = None  # None表示本轮没检测到目标，fusion判断时按"没有干扰物"处理
    last_gaze_oled = (OLED_W // 2, OLED_H // 2)

    try:
        while True:
            now = time.time()

            # --- 真实注视点：GC0308 + EllSeg + 标定矩阵（和phase1_fusion.py完全一致，未改动） ---
            ret, frame = cap.read()
            if ret:
                gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
                crop = gray_full[ry:ry + rh, rx:rx + rw]
                pres = detect_pupil(crop)
                eye_vis = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
                if pres["success"]:
                    px, py = pres["pupil_cx"], pres["pupil_cy"]
                    oled_xy = A @ np.array([px, py, 1.0])
                    last_gaze_oled = (float(oled_xy[0]), float(oled_xy[1]))
                    cv2.ellipse(eye_vis, pres["ellipse"], (0, 255, 0), 1)
                else:
                    cv2.putText(eye_vis, "pupil not found (using last known gaze)",
                                (3, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
                cv2.imshow("GC0308 crop (real-time)", eye_vis)

            gaze_x, gaze_y = last_gaze_oled
            gaze_x_clamped = float(np.clip(gaze_x, 0, OLED_W - 1))
            gaze_y_clamped = float(np.clip(gaze_y, 0, OLED_H - 1))

            # --- 场景画面 + 真实YOLO检测：每1秒跑一次，不是每帧都跑(YOLO在CPU上
            # 有真实耗时，不需要跟眼动检测一样的帧率，场景里物体位置变化本来就慢) ---
            if now - last_detect_run > 1.0:
                scene_img = fetch_capture(base_url)
                if scene_img is not None:
                    t0 = time.time()
                    current_object_scene = detect_target(model, scene_img, target_class_id, YOLO_CONF_THRESHOLD)
                    infer_ms = (time.time() - t0) * 1000
                    if current_object_scene:
                        print(f"  [YOLO] 检测到'{args.target_class}' conf={current_object_scene['conf']:.2f} "
                              f"rect={current_object_scene} (推理耗时{infer_ms:.0f}ms)")
                    else:
                        print(f"  [YOLO] 未检测到'{args.target_class}' (推理耗时{infer_ms:.0f}ms)")
                last_detect_run = now

            if scene_img is not None:
                scene_vis = scene_img.copy()
                if current_object_scene:
                    r = current_object_scene
                    cv2.rectangle(scene_vis, (r["x"], r["y"]), (r["x"] + r["w"], r["y"] + r["h"]),
                                  (0, 255, 0), 2)
                    cv2.putText(scene_vis, f"YOLO: {args.target_class} {r['conf']:.2f}",
                                (r["x"], max(15, r["y"] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                else:
                    cv2.putText(scene_vis, f"YOLO: no '{args.target_class}' detected",
                                (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                cv2.imshow("ESP32CAM scene (real YOLO detection)", scene_vis)

            # --- OLED坐标系预览画布 ---
            canvas = np.zeros((OLED_H * DISPLAY_SCALE, OLED_W * DISPLAY_SCALE, 3), dtype=np.uint8)
            object_oled = scene_rect_to_oled(current_object_scene) if current_object_scene else None
            if object_oled:
                cv2.rectangle(canvas,
                              (object_oled["x"] * DISPLAY_SCALE, object_oled["y"] * DISPLAY_SCALE),
                              ((object_oled["x"] + object_oled["w"]) * DISPLAY_SCALE,
                               (object_oled["y"] + object_oled["h"]) * DISPLAY_SCALE),
                              (0, 255, 0), 2)
                cv2.putText(canvas, f"REAL YOLO: {args.target_class}",
                            (object_oled["x"] * DISPLAY_SCALE, max(15, object_oled["y"] * DISPLAY_SCALE - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            inside = bool(object_oled) and rect_contains(object_oled, gaze_x_clamped, gaze_y_clamped)
            gaze_color = (0, 0, 255) if inside else (0, 255, 0)
            cv2.circle(canvas, (int(gaze_x_clamped * DISPLAY_SCALE), int(gaze_y_clamped * DISPLAY_SCALE)),
                       6, gaze_color, -1)
            cv2.putText(canvas, "REAL GAZE (GC0308+EllSeg+calibration)",
                        (5, OLED_H * DISPLAY_SCALE - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, gaze_color, 1)
            status_text = f"gaze=({gaze_x_clamped:.0f},{gaze_y_clamped:.0f}) inside={inside} mask_active={mask_active}"
            cv2.putText(canvas, status_text, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            cv2.imshow("OLED-space (real gaze + real YOLO detection)", canvas)

            # --- 融合逻辑：状态跳变才发请求，原样复用已验证过的防抖状态机 ---
            if inside and not mask_active:
                print(f"[{time.strftime('%H:%M:%S')}] 真实注视点进入真实检测到的'{args.target_class}' -> 发送遮挡指令")
                send_mask(base_url, object_oled, True)
                mask_active = True
            elif not inside and mask_active:
                print(f"[{time.strftime('%H:%M:%S')}] 注视点离开/目标消失 -> 发送清除指令")
                send_mask(base_url, {"x": 0, "y": 0, "w": OLED_W, "h": OLED_H}, False)
                mask_active = False

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
    except KeyboardInterrupt:
        print("\n检测到中断(Ctrl+C)，清理中...")

    if mask_active:
        print("\n退出前清除OLED遮挡...")
        send_mask(base_url, {"x": 0, "y": 0, "w": OLED_W, "h": OLED_H}, False)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
