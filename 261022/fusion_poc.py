"""
261022 -- PC端融合判断 PoC（Proof of Concept）

目的：验证"判断是否该遮挡 -> 发/mask指令"这条逻辑链路本身，而不是去冒充
已经集成了真实的眼动追踪和真实的干扰物检测——这两块现在都还没有可信的
结果可用，不能假装有：

  - 眼动追踪：261004里EllSeg给出的是瞳孔在眼部摄像头画面里的像素坐标，
    还没有标定成"对应OLED/场景画面里的哪个位置"。261004/experiment_report.md
    第7c.3节明确记录过：5点注视标定因IR光源手持不稳定、脚本缺图片审计能力
    等问题，数据不可信，标定这一步至今没有真正跑通产出可信结果。
  - 干扰物检测：261022/README.md里已经写明这个阶段"物体检测放到PC端做，
    或者先用一个固定的手动矩形模拟干扰物验证链路"——本脚本采用后者。

本脚本实际做的事（都是真实的，不是模拟）：
  1. 真实轮询ESP32CAM的 /capture，显示真实场景画面——但目前只作参考展示，
     不参与下面的融合判断逻辑（还没有物体检测模型可以从这张图里找出
     "干扰物在哪"）。
  2. 真实调用ESP32CAM的 /mask 接口，真实控制OLED画面。

本脚本用来代替真实数据的部分（明确标注，不是最终实现）：
  1. "当前注视位置"：用键盘WASD手动移动一个点，直接定义在OLED坐标系
     (128x64)下，不经过任何真实眼动数据——因为目前没有可信的
     瞳孔坐标->OLED坐标映射关系可用。
  2. "干扰物位置"：一个写死的固定矩形，同样定义在OLED坐标系下。

核心融合逻辑（这是本脚本真正要验证的东西）：每帧检查模拟注视点是否落入
模拟干扰物矩形，只在"进入/离开"这个状态发生跳变的瞬间才真实发送一次
HTTP /mask 请求，而不是每帧都发——验证的是这套"防抖+状态机"的逻辑和
真实HTTP时序能不能正确配合，不是验证检测精度。

等261004那边的标定完成、物体检测模型选定后，只需要把下面
get_simulated_gaze()（目前是读键盘）和 FAKE_OBJECT_RECT（目前是写死的字典）
换成真实实现，核心的状态机/防抖/HTTP触发逻辑不需要改。

Usage:
    python fusion_poc.py --ip 172.20.10.2

操作：
    先用鼠标点一下弹出的"OLED-space"预览窗口，让它获得键盘焦点，
    然后用 W/A/S/D 移动模拟注视点（红点=在干扰物区域内，绿点=不在），
    按 q 退出（退出前会自动给OLED发送清除指令，不会留一个卡住的遮挡画面）。
"""
import argparse
import time
import urllib.request
import urllib.error

import cv2
import numpy as np

OLED_W, OLED_H = 128, 64
SCALE = 4  # 128x64裸眼看点太小，放大4倍显示（不影响实际发给OLED的坐标）

# 写死的"干扰物"矩形，占位用 -- 真实物体检测模型接入后，这里要换成
# "场景摄像头检测框 -> OLED坐标系"的真实映射结果，而不是这个固定值
FAKE_OBJECT_RECT = {"x": 70, "y": 15, "w": 40, "h": 30}

GAZE_STEP = 4  # 每次按键，模拟注视点在OLED坐标系下移动的像素数


def http_get(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.URLError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


def send_mask(base_url, rect, on):
    url = f"{base_url}/mask?x={rect['x']}&y={rect['y']}&w={rect['w']}&h={rect['h']}&on={1 if on else 0}"
    status, body = http_get(url)
    tag = "ON " if on else "OFF"
    print(f"  [mask {tag}] {url} -> {status} {body}")


def rect_contains(rect, px, py):
    return rect["x"] <= px < rect["x"] + rect["w"] and rect["y"] <= py < rect["y"] + rect["h"]


def fetch_capture(base_url):
    """拉一帧场景摄像头画面，仅供人看作参考，目前不参与融合判断逻辑。"""
    try:
        with urllib.request.urlopen(f"{base_url}/capture", timeout=3) as resp:
            data = resp.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True, help="ESP32CAM的IP地址")
    args = parser.parse_args()
    base_url = f"http://{args.ip}"

    gaze_x, gaze_y = OLED_W // 2, OLED_H // 2
    mask_active = False

    print("先点一下'OLED-space'预览窗口获得焦点，再用 W/A/S/D 移动模拟注视点，q 退出")
    print("（退出前会自动清除OLED上的遮挡，不会留一个卡住的画面）\n")

    last_capture_fetch = 0.0
    scene_img = None

    while True:
        now = time.time()
        if now - last_capture_fetch > 1.0:  # 场景画面纯展示用，每秒刷新一次即可，不用太频繁
            scene_img = fetch_capture(base_url)
            last_capture_fetch = now

        # --- OLED坐标系预览画布（放大SCALE倍） ---
        canvas = np.zeros((OLED_H * SCALE, OLED_W * SCALE, 3), dtype=np.uint8)
        r = FAKE_OBJECT_RECT
        cv2.rectangle(canvas,
                      (r["x"] * SCALE, r["y"] * SCALE),
                      ((r["x"] + r["w"]) * SCALE, (r["y"] + r["h"]) * SCALE),
                      (0, 165, 255), 2)  # 橙色框 = 写死的模拟干扰物位置，不是真实检测结果
        cv2.putText(canvas, "FAKE OBJECT (hardcoded, not real detection)",
                    (r["x"] * SCALE, max(15, r["y"] * SCALE - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

        inside = rect_contains(r, gaze_x, gaze_y)
        gaze_color = (0, 0, 255) if inside else (0, 255, 0)
        cv2.circle(canvas, (gaze_x * SCALE, gaze_y * SCALE), 6, gaze_color, -1)
        cv2.putText(canvas, "SIMULATED GAZE (WASD, not real eye tracking)",
                    (5, OLED_H * SCALE - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, gaze_color, 1)

        status_text = f"gaze=({gaze_x},{gaze_y}) inside_object={inside} mask_active={mask_active}"
        cv2.putText(canvas, status_text, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.imshow("OLED-space (simulated gaze + fake object)", canvas)

        if scene_img is not None:
            cv2.imshow("ESP32CAM scene /capture (reference only, not linked to logic yet)", scene_img)

        # --- 核心融合逻辑：只在状态跳变时发送HTTP请求，不是每帧都发 ---
        if inside and not mask_active:
            print(f"[{time.strftime('%H:%M:%S')}] 注视点进入干扰物区域 -> 发送遮挡指令")
            send_mask(base_url, r, True)
            mask_active = True
        elif not inside and mask_active:
            print(f"[{time.strftime('%H:%M:%S')}] 注视点离开干扰物区域 -> 发送清除指令")
            send_mask(base_url, {"x": 0, "y": 0, "w": OLED_W, "h": OLED_H}, False)
            mask_active = False

        key = cv2.waitKey(30) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('a'):
            gaze_x = max(0, gaze_x - GAZE_STEP)
        elif key == ord('d'):
            gaze_x = min(OLED_W - 1, gaze_x + GAZE_STEP)
        elif key == ord('w'):
            gaze_y = max(0, gaze_y - GAZE_STEP)
        elif key == ord('s'):
            gaze_y = min(OLED_H - 1, gaze_y + GAZE_STEP)

    if mask_active:
        print("\n退出前清除OLED遮挡...")
        send_mask(base_url, {"x": 0, "y": 0, "w": OLED_W, "h": OLED_H}, False)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
