import cv2

for idx in [0, 1]:
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"index {idx}: failed to open")
        continue
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    # warm up a few frames (first frames can be dark/uninitialized)
    for _ in range(10):
        cap.read()
    ret, frame = cap.read()
    if ret:
        filename = f"identify_index_{idx}.png"
        cv2.imwrite(filename, frame)
        print(f"index {idx}: saved {filename}, shape={frame.shape}")
    else:
        print(f"index {idx}: failed to read frame")
    cap.release()
