"""
GC0308 module - Step 2: resolution/FPS measurement.

Same methodology as the OV9281 test (camera_test.py in the parent directory):
measured_fps = frames_captured / elapsed_wall_clock_seconds, over >=5 seconds
of continuous reading -- never trust cv2.CAP_PROP_FPS alone.

Index confirmed via identify_gc0308.py: index 1 = GC0308 (monochrome, close-up
IR eye image), index 0 = Integrated Camera (color).
"""
import cv2
import time
import json

CAMERA_INDEX = 1  # confirmed via identify_gc0308.py visual check


def measure_fps(width, height, duration=5.0):
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    reported_fps = cap.get(cv2.CAP_PROP_FPS)

    for _ in range(10):
        cap.read()  # warm up

    frames = 0
    failed = 0
    start = time.time()
    while time.time() - start < duration:
        ret, frame = cap.read()
        if ret:
            frames += 1
        else:
            failed += 1
    elapsed = time.time() - start
    cap.release()

    return {
        "requested_width": width, "requested_height": height,
        "actual_width": actual_w, "actual_height": actual_h,
        "reported_fps_CAP_PROP": reported_fps,
        "frames_captured": frames, "dropped_failed_frames": failed,
        "elapsed_seconds": round(elapsed, 3),
        "measured_fps": round(frames / elapsed, 2) if elapsed > 0 else 0,
    }


def main():
    print("=" * 60)
    print(f"GC0308 FPS measurement (index {CAMERA_INDEX})")
    print("=" * 60)

    # Query native/default resolution first
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    default_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    default_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    print(f"Default resolution reported: {default_w}x{default_h}")

    # Try the module's advertised spec (claimed 120fps high-speed) plus a
    # couple of fallback resolutions in case the requested mode isn't honored.
    test_resolutions = [(default_w, default_h), (640, 480), (320, 240)]
    # de-duplicate while preserving order
    seen = set()
    test_resolutions = [r for r in test_resolutions if not (r in seen or seen.add(r))]

    results = []
    for (w, h) in test_resolutions:
        print(f"\nTesting {w}x{h} for 5 seconds...")
        res = measure_fps(w, h, duration=5.0)
        if res is None:
            print("  FAILED to open camera")
            continue
        results.append(res)
        print(f"  requested={w}x{h} actual={res['actual_width']}x{res['actual_height']} "
              f"reported_fps(CAP_PROP)={res['reported_fps_CAP_PROP']} "
              f"measured_fps={res['measured_fps']} frames={res['frames_captured']} "
              f"dropped={res['dropped_failed_frames']}")

    with open("gc0308_fps_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nSaved to gc0308_fps_results.json")

if __name__ == "__main__":
    main()
