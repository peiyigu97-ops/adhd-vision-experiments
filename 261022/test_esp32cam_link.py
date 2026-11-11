"""
261022 -- PC侧测试客户端，配合 esp32cam_wifi_mask_server.ino 使用。

用途：烧录固件后，用这个脚本从PC端验证ESP32CAM的三个HTTP接口是否都正常工作，
不涉及眼动检测/干扰物判断的融合逻辑（那部分等DeepVOG测试结果出来后再接入）。

这是纯链路验证脚本，不是最终产品代码。

Usage:
    python test_esp32cam_link.py --ip <ESP32CAM的IP地址>

依次执行：
    1. GET /status   -- 确认WiFi/摄像头/OLED是否都初始化成功
    2. GET /capture   -- 抓一帧JPEG，存到本地看看画面对不对
    3. GET /mask      -- 在OLED左上角画一个测试遮挡块，持续2秒后清除
"""
import argparse
import time
import urllib.request
import json
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_captures")


def imwrite_unicode(path, data_bytes):
    """本项目路径含中文字符(作品集/课程)，用二进制直写代替依赖OpenCV的imwrite,
    绕开同一类路径编码问题（在261004已反复踩过这个坑）。"""
    with open(path, "wb") as f:
        f.write(data_bytes)


def check_status(base_url):
    print(f"GET {base_url}/status")
    with urllib.request.urlopen(f"{base_url}/status", timeout=5) as resp:
        data = json.loads(resp.read().decode())
    print(f"  wifi_connected = {data.get('wifi_connected')}")
    print(f"  camera_ok      = {data.get('camera_ok')}")
    print(f"  oled_ok        = {data.get('oled_ok')}")
    print(f"  ip             = {data.get('ip')}")
    if not data.get("camera_ok"):
        print("  WARNING: camera_ok=false, /capture 会失败")
    if not data.get("oled_ok"):
        print("  WARNING: oled_ok=false, /mask 会失败")
    return data


def test_capture(base_url):
    print(f"\nGET {base_url}/capture")
    t0 = time.time()
    with urllib.request.urlopen(f"{base_url}/capture", timeout=10) as resp:
        jpeg_bytes = resp.read()
    elapsed = time.time() - t0
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"capture_{int(time.time())}.jpg")
    imwrite_unicode(path, jpeg_bytes)
    print(f"  {len(jpeg_bytes)} bytes, {elapsed*1000:.0f}ms, saved to {path}")


def test_mask(base_url):
    print(f"\nGET {base_url}/mask (draw test block, then clear after 2s)")
    url_on = f"{base_url}/mask?x=0&y=0&w=40&h=20&on=1"
    with urllib.request.urlopen(url_on, timeout=5) as resp:
        print(f"  draw: {resp.read().decode()}")
    time.sleep(2.0)
    url_off = f"{base_url}/mask?x=0&y=0&w=128&h=64&on=0"
    with urllib.request.urlopen(url_off, timeout=5) as resp:
        print(f"  clear: {resp.read().decode()}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True, help="ESP32CAM的IP地址，例如 192.168.1.50")
    args = parser.parse_args()

    base_url = f"http://{args.ip}"

    status = check_status(base_url)

    if status.get("camera_ok"):
        test_capture(base_url)
    else:
        print("\nSkip /capture test (camera_ok=false)")

    if status.get("oled_ok"):
        test_mask(base_url)
    else:
        print("\nSkip /mask test (oled_ok=false)")

    print("\nDone.")


if __name__ == "__main__":
    main()
