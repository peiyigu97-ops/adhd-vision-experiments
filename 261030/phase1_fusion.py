"""
261030 Phase1 -- 真实融合主程序。

替换掉`261022/fusion_poc.py`里两处明确标注过的模拟数据中的第一处（见
`261022/README.md`"后续要把这个PoC换成真实融合逻辑，需要"列表第1项）：

  - "当前注视位置"：原来是WASD键盘模拟，这次换成GC0308+EllSeg+标定矩阵
    算出来的真实注视点（已经在OLED坐标系下，不需要额外换算）。
  - "干扰物位置"：**这次仍然是模拟的**，按Phase1范围明确不做真实物体检测
    （见261014文档第八节"Phase1...不碰FOMO"），这不是本次遗漏，是预先
    划定的范围边界，和注视点那一半不一样——不要把这两者混为一谈。

核心的"状态跳变才发/mask请求"防抖逻辑原样复用自fusion_poc.py，没有改动
（该逻辑已在2026-10-25验证过真实HTTP时序正确，见261022/README.md"验证
结果"一节），这次只是把"进入判定"的输入源从键盘换成真实数据。

场景摄像头(ESP32-CAM QVGA 320x240)->OLED(128x64)这一步的坐标换算，用的
是最简单的线性等比例缩小（scale_x = 128/320, scale_y = 64/240），**这是
一个有意的简化占位，不是正式的几何标定**——正式标定需要装好光学透镜后，
用外部参照相机拍OLED反射到真实世界的落点才能做，这是独立于本次Phase1的
工作，见261030/README.md"场景摄像头→OLED的映射"一节。

Usage:
    python phase1_fusion.py --esp32-ip 172.20.10.2
    (需要先跑 calibration_gc0308_oled.py 产出 gc0308_oled_calibration.json，
    本脚本找不到这个文件会直接报错退出，不会用假数据顶替)
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

_PROJ_261004 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "261004"))
sys.path.insert(0, _PROJ_261004)
from pupil_detector_ellseg import detect_pupil  # noqa: E402 -- 只要EllSeg的detect_pupil，
# 不要依赖Haar cascade的detect_eye，原因见calibration_gc0308_oled.py docstring

BASE = os.path.dirname(os.path.abspath(__file__))
CALIB_JSON_PATH = os.path.join(BASE, "gc0308_oled_calibration.json")

OLED_W, OLED_H = 128, 64
SCENE_W, SCENE_H = 320, 240  # ESP32-CAM固件里配置的QVGA分辨率(esp32cam_wifi_mask_server.ino)
SCENE_TO_OLED_SX = OLED_W / SCENE_W
SCENE_TO_OLED_SY = OLED_H / SCENE_H

DISPLAY_SCALE = 4  # OLED坐标系预览画布放大倍数(128x64裸眼太小)，不影响真实发给OLED的坐标

# 写死的"干扰物"矩形，定义在**场景摄像头QVGA画面**的像素坐标系下（不是OLED坐标系），
# 这样可以叠加画在真实抓回来的/capture画面上，直观看出"这个框对应场景里哪块地方"。
# 真实物体检测接入后，这里要换成检测框的真实输出，仍然是场景画面坐标系。
# 2026-11-04调大：第一次联调时用的是100x70(换算到OLED只有40x19px)，用户反馈
# OLED上亮起来的区域太小看不清楚，调大到接近半屏，方便目视确认链路本身是否
# work——等真实物体检测接入后，这个尺寸不再有意义，会被检测框的真实大小取代。
FAKE_OBJECT_RECT_SCENE = {"x": 100, "y": 20, "w": 180, "h": 140}


def scene_rect_to_oled(rect):
    """把场景摄像头坐标系下的矩形，线性缩放换算到OLED坐标系——见本文件
    docstring，这是占位简化，不是正式几何标定。"""
    return {
        "x": int(round(rect["x"] * SCENE_TO_OLED_SX)),
        "y": int(round(rect["y"] * SCENE_TO_OLED_SY)),
        "w": int(round(rect["w"] * SCENE_TO_OLED_SX)),
        "h": int(round(rect["h"] * SCENE_TO_OLED_SY)),
    }


def rect_contains(rect, px, py):
    return rect["x"] <= px < rect["x"] + rect["w"] and rect["y"] <= py < rect["y"] + rect["h"]


def http_get(url, timeout=10):
    """timeout调到10秒(原来3秒)：2026-11-04首次联调发现，/mask请求会偶尔被
    ESP32正在处理的/capture请求挡住排队(WebServer库单线程同步处理，一次只能
    服务一个请求)，3秒内等不到响应就被判超时，但OLED其实已经真的画出来了——
    是客户端等得不够久，不是指令没送达。调长超时，避免把"慢但成功"误判成
    "失败"。这不能根治"/mask可能要等/capture处理完"这个排队问题，只是让客户端
    不要在真正成功的请求上过早报错；如果延迟真的影响到实际使用体验(比如用户
    已经转移视线很久了遮挡才姗姗来迟)，需要回到ESP32固件这边优化，比如降低
    /capture的轮询频率，或者给/mask单独开一个端口/更高优先级。"""
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
            f"找不到 {CALIB_JSON_PATH} -- 先跑 calibration_gc0308_oled.py 产出这个文件，"
            "本脚本不会用假数据顶替一个没做过的标定。"
        )
    with open(CALIB_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"加载标定: camera_index={data['camera_index']}, "
          f"crop_roi={data['crop_roi']}, 标定平均误差={data['mean_error_px']:.1f}px "
          f"(标定于{data['run_tag']})")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--esp32-ip", required=True, help="ESP32CAM的IP地址")
    args = parser.parse_args()
    base_url = f"http://{args.esp32_ip}"

    calib = load_calibration()
    cam_index = calib["camera_index"]
    roi = calib["crop_roi"]
    rx, ry, rw, rh = roi["x"], roi["y"], roi["w"], roi["h"]
    A = np.array(calib["affine_matrix"])  # oled = A @ [pupil_x_crop, pupil_y_crop, 1]

    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"打不开GC0308 index={cam_index} -- 物理连接变了的话，重新跑一遍标定脚本"
              "(它会用新的index重新存一份calibration JSON)")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    for _ in range(10):
        cap.read()

    fake_object_oled = scene_rect_to_oled(FAKE_OBJECT_RECT_SCENE)
    print(f"\n假干扰物(场景坐标){FAKE_OBJECT_RECT_SCENE} -> 换算到OLED坐标{fake_object_oled}")
    print("这次注视点是真实的GC0308+EllSeg数据，不是键盘模拟。按q退出"
          "(退出前会自动清除OLED，不留卡住的画面)。\n")

    mask_active = False
    last_capture_fetch = 0.0
    scene_img = None
    last_gaze_oled = (OLED_W // 2, OLED_H // 2)  # 瞳孔检测失败的帧，沿用上一次的有效位置，
    # 不要让"检测失败"瞬间让注视点跳回画面中心，那会在fusion状态机里制造假的"离开"事件

    try:
        while True:
            now = time.time()

            # --- 真实注视点：GC0308 + EllSeg + 标定矩阵 ---
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
            # 裁掉标定外推可能跑出OLED画面范围的坐标，不让它直接污染/mask请求
            gaze_x_clamped = float(np.clip(gaze_x, 0, OLED_W - 1))
            gaze_y_clamped = float(np.clip(gaze_y, 0, OLED_H - 1))

            # --- 场景画面：真实轮询，仅作参考展示 + 叠加假干扰物框，不参与判断逻辑的输入源 ---
            if now - last_capture_fetch > 1.0:
                scene_img = fetch_capture(base_url)
                last_capture_fetch = now
            if scene_img is not None:
                scene_vis = scene_img.copy()
                r = FAKE_OBJECT_RECT_SCENE
                cv2.rectangle(scene_vis, (r["x"], r["y"]), (r["x"] + r["w"], r["y"] + r["h"]),
                              (0, 165, 255), 2)
                cv2.putText(scene_vis, "FAKE OBJECT (hardcoded, not real detection)",
                            (r["x"], max(15, r["y"] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1)
                cv2.imshow("ESP32CAM scene /capture (reference only)", scene_vis)

            # --- OLED坐标系预览画布 ---
            canvas = np.zeros((OLED_H * DISPLAY_SCALE, OLED_W * DISPLAY_SCALE, 3), dtype=np.uint8)
            fr = fake_object_oled
            cv2.rectangle(canvas,
                          (fr["x"] * DISPLAY_SCALE, fr["y"] * DISPLAY_SCALE),
                          ((fr["x"] + fr["w"]) * DISPLAY_SCALE, (fr["y"] + fr["h"]) * DISPLAY_SCALE),
                          (0, 165, 255), 2)
            cv2.putText(canvas, "FAKE OBJECT (scaled from scene rect, not real detection)",
                        (fr["x"] * DISPLAY_SCALE, max(15, fr["y"] * DISPLAY_SCALE - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

            inside = rect_contains(fr, gaze_x_clamped, gaze_y_clamped)
            gaze_color = (0, 0, 255) if inside else (0, 255, 0)
            cv2.circle(canvas, (int(gaze_x_clamped * DISPLAY_SCALE), int(gaze_y_clamped * DISPLAY_SCALE)),
                       6, gaze_color, -1)
            cv2.putText(canvas, "REAL GAZE (GC0308+EllSeg+calibration, not simulated)",
                        (5, OLED_H * DISPLAY_SCALE - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, gaze_color, 1)
            status_text = f"gaze=({gaze_x_clamped:.0f},{gaze_y_clamped:.0f}) inside={inside} mask_active={mask_active}"
            cv2.putText(canvas, status_text, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
            cv2.imshow("OLED-space (real gaze + fake object)", canvas)

            # --- 融合逻辑：原样复用fusion_poc.py已验证过的防抖状态机，只换了inside的输入源 ---
            if inside and not mask_active:
                print(f"[{time.strftime('%H:%M:%S')}] 真实注视点进入干扰物区域 -> 发送遮挡指令")
                send_mask(base_url, fr, True)
                mask_active = True
            elif not inside and mask_active:
                print(f"[{time.strftime('%H:%M:%S')}] 真实注视点离开干扰物区域 -> 发送清除指令")
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
