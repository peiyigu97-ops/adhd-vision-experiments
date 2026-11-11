"""
261022 -- 给作品集拍照用的"双摄像头弹窗"脚本。

同时弹出两个实时画面窗口：
  1. ESP32CAM 外部场景摄像头（通过 /capture 轮询抓拍，走HTTP，不是本机USB设备）
  2. GC0308 眼动摄像头（通过 cv2.VideoCapture 本机USB设备读取）

纯展示/拍照用途，不做任何检测或融合逻辑判断。按 q 或关闭窗口退出，
退出时会清理掉两个摄像头的连接。

Usage:
    python show_both_cameras.py --ip <ESP32CAM的IP> [--gc-index 1]

默认 --gc-index=1，这是 261030/calibration_gc0308_oled.py 里用的同一个默认值，
但USB设备index在重新插拔后可能漂移（见261004/gc0308/identify_gc0308.py开头
的说明），如果打不开或者画面明显不对（比如打开的是别的摄像头），先跑
`261004/gc0308/identify_gc0308.py` 核实实际index，再用 --gc-index 指定。
"""
import argparse
import time

import cv2
import numpy as np
import urllib.request

ESP32_WINDOW = "ESP32CAM scene camera"
GC_WINDOW = "GC0308 eye camera"


def fetch_esp32_frame(base_url, timeout=3.0):
    """轮询 /capture 拿一帧JPEG并解码成BGR图像。失败返回None，不抛异常，
    这样ESP32偶发一次超时不会把整个弹窗脚本带崩。"""
    try:
        with urllib.request.urlopen(f"{base_url}/capture", timeout=timeout) as resp:
            jpeg_bytes = resp.read()
        arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        print(f"[ESP32CAM] 抓帧失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="同时弹出ESP32CAM和GC0308的实时画面窗口，用于拍照")
    parser.add_argument("--ip", required=True, help="ESP32CAM的IP地址")
    parser.add_argument("--gc-index", type=int, default=1, help="GC0308在本机的摄像头index（默认1，和261030标定脚本一致）")
    args = parser.parse_args()

    base_url = f"http://{args.ip}"

    print(f"ESP32CAM: {base_url}/capture (轮询抓拍)")
    print(f"GC0308:   cv2.VideoCapture(index={args.gc_index})")

    gc_cap = cv2.VideoCapture(args.gc_index, cv2.CAP_DSHOW)
    if not gc_cap.isOpened():
        print(f"[GC0308] 打不开摄像头 index={args.gc_index} -- 先跑 261004/gc0308/identify_gc0308.py 核实index")
        gc_cap = None

    # 两个窗口默认都会开在屏幕同一个位置互相完全遮挡，之前排查"GC0308显示成
    # 笔记本摄像头"的问题实际是这个——人眼只看到了最上层那个窗口，误以为
    # 下面被盖住的窗口内容是错的。这里手动错开摆放位置，确保两个窗口同时可见。
    cv2.namedWindow(ESP32_WINDOW, cv2.WINDOW_NORMAL)
    cv2.moveWindow(ESP32_WINDOW, 50, 80)
    cv2.resizeWindow(ESP32_WINDOW, 480, 360)
    if gc_cap is not None:
        cv2.namedWindow(GC_WINDOW, cv2.WINDOW_NORMAL)
        cv2.moveWindow(GC_WINDOW, 600, 80)
        cv2.resizeWindow(GC_WINDOW, 480, 360)

    print("两个窗口已弹出（左：ESP32CAM，右：GC0308），q 或关闭窗口退出。")

    last_esp32_frame = None
    try:
        while True:
            # ESP32CAM是轮询式抓拍，不是连续流，这里每轮循环重新请求一次。
            frame = fetch_esp32_frame(base_url)
            if frame is not None:
                last_esp32_frame = frame
            if last_esp32_frame is not None:
                cv2.imshow(ESP32_WINDOW, last_esp32_frame)

            if gc_cap is not None:
                ok, gc_frame = gc_cap.read()
                if ok:
                    cv2.imshow(GC_WINDOW, gc_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            # ESP32CAM这边不用太高频轮询，省得给板子太大压力；GC0308这边
            # 走的是上面waitKey(1)的节奏，不额外sleep。
            time.sleep(0.05)
    finally:
        if gc_cap is not None:
            gc_cap.release()
        cv2.destroyAllWindows()
        print("已退出，摄像头连接已释放。")


if __name__ == "__main__":
    main()
