import cv2
import time

# 先尝试打开 OpenAICam
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("无法打开摄像头")
    exit()

# 尝试设置 OV9281 的分辨率
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

print(f"实际分辨率: {int(width)} × {int(height)}")
print("开始测试 FPS，请等待 5 秒...")

frames = 0
start = time.time()

while time.time() - start < 5:
    ret, frame = cap.read()

    if ret:
        frames += 1

fps = frames / (time.time() - start)

print(f"实际 FPS: {fps:.2f}")

cap.release()