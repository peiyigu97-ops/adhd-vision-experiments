"""
STEP 3-4: OV9281 camera detection and resolution/FPS measurement.

Enumerates camera indices 0-4, tries DirectShow backend first (falls back to
default backend if DSHOW fails to open), and for any index that opens, reports
backend name, resolution, and a device name hint read from the DirectShow
filter graph via pygrabber if available (optional, not required).

For the index that appears to be OV9281 (monochrome, high FPS), it tests
640x480 and 1280x720 by actually reading frames for 5 seconds and computing
frames / elapsed_time -- NOT just reading CAP_PROP_FPS.
"""
import cv2
import time
import json

RESULTS = []

def test_index(idx, backend, backend_name):
    cap = cv2.VideoCapture(idx, backend)
    if not cap.isOpened():
        return None
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    reported_fps = cap.get(cv2.CAP_PROP_FPS)
    ret, frame = cap.read()
    readable = ret and frame is not None
    shape = frame.shape if readable else None
    cap.release()
    return {
        "index": idx,
        "backend": backend_name,
        "default_width": w,
        "default_height": h,
        "reported_fps": reported_fps,
        "frame_readable": readable,
        "frame_shape": shape,
    }

def measure_fps(idx, backend, width, height, duration=5.0):
    cap = cv2.VideoCapture(idx, backend)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

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
        "requested_width": width,
        "requested_height": height,
        "actual_width": actual_w,
        "actual_height": actual_h,
        "frames_captured": frames,
        "dropped_failed_frames": failed,
        "elapsed_seconds": round(elapsed, 3),
        "measured_fps": round(frames / elapsed, 2) if elapsed > 0 else 0,
    }

def main():
    print("=" * 60)
    print("STEP 3: Enumerating camera indices 0-4 (DirectShow backend)")
    print("=" * 60)

    found = []
    for idx in range(5):
        info = test_index(idx, cv2.CAP_DSHOW, "DSHOW")
        if info is None:
            print(f"  index {idx}: not opened (DSHOW)")
            continue
        print(f"  index {idx}: OPENED -- default {info['default_width']}x{info['default_height']}, "
              f"reported_fps={info['reported_fps']}, frame_readable={info['frame_readable']}, "
              f"shape={info['frame_shape']}")
        found.append(info)
        RESULTS.append(info)

    if not found:
        print("\nNo camera opened via DSHOW. Trying default backend (CAP_ANY) as fallback...")
        for idx in range(5):
            info = test_index(idx, cv2.CAP_ANY, "ANY/default")
            if info is None:
                print(f"  index {idx}: not opened (ANY)")
                continue
            print(f"  index {idx}: OPENED -- default {info['default_width']}x{info['default_height']}, "
                  f"reported_fps={info['reported_fps']}, frame_readable={info['frame_readable']}, "
                  f"shape={info['frame_shape']}")
            found.append(info)
            RESULTS.append(info)

    if not found:
        print("\nNo camera could be opened by any backend. Stopping here.")
        with open("camera_enum_results.json", "w") as f:
            json.dump({"enumeration": RESULTS, "fps_tests": []}, f, indent=2, default=str)
        return

    print("\nCandidates found at indices:", [f["index"] for f in found])
    print("NOTE: identifying which index is OV9281 (OpenAICam) requires visual")
    print("confirmation -- grayscale/monochrome image, or matching resolution")
    print("behavior. Do not assume index 1.")

    print("\n" + "=" * 60)
    print("STEP 4: Measuring actual FPS for each candidate (640x480 and 1280x720)")
    print("=" * 60)

    fps_tests = []
    for info in found:
        idx = info["index"]
        backend = cv2.CAP_DSHOW if info["backend"] == "DSHOW" else cv2.CAP_ANY
        for (w, h) in [(640, 480), (1280, 720)]:
            print(f"\n  Testing index {idx} at {w}x{h} for 5 seconds...")
            result = measure_fps(idx, backend, w, h, duration=5.0)
            if result is None:
                print(f"    FAILED to open index {idx} for FPS test")
                continue
            result["index"] = idx
            result["backend"] = info["backend"]
            fps_tests.append(result)
            print(f"    requested={w}x{h} actual={result['actual_width']}x{result['actual_height']} "
                  f"measured_fps={result['measured_fps']} frames={result['frames_captured']} "
                  f"dropped={result['dropped_failed_frames']}")

    with open("camera_enum_results.json", "w") as f:
        json.dump({"enumeration": RESULTS, "fps_tests": fps_tests}, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("Results saved to camera_enum_results.json")
    print("=" * 60)
    print("\nPlease visually check which index showed the OV9281 image")
    print("(monochrome/grayscale, wide FOV) during this test, since this")
    print("script cannot confirm device identity by name alone.")

if __name__ == "__main__":
    main()
