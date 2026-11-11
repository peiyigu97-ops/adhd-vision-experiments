"""
STEP 7: Real-time eye ROI experiment.

No IR illuminator yet, so this stage does NOT assume stable automatic
detection. Two approaches are combined:

  Plan B (tried first): OpenCV's bundled Haar cascades (classical method,
  no extra model download) -- frontal face detection first, then eye
  detection restricted to the face region (narrows search, improves
  stability vs. running eye cascade on the full 105 deg FOV frame).

  Plan A (manual fallback): press 'm' to pause on the current frame and
  manually drag a box around one eye with cv2.selectROI. Use this if Haar
  auto-detection is unstable or fails, which is expected to be common given
  small eye size within the wide FOV frame.

Controls:
  m -- pause and manually select one eye ROI on current frame
  s -- save current auto-detected eye ROI (if available)
  q -- quit

Every saved ROI crop goes to data/eye/ with a timestamp filename.
Displays: original frame with rectangle(s) drawn + a separate ROI window.
"""
import cv2
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
EYE_DIR = os.path.join(BASE, "data", "eye")
os.makedirs(EYE_DIR, exist_ok=True)

# Re-verified 2026-10-08 via identify_camera.py: index mapping had flipped
# (was 1=OV9281 on 2026-10-04, now 0=OV9281) after a USB re-enumeration event.
# If captures look wrong (unexpectedly dark, or colored instead of monochrome),
# rerun identify_camera.py to reconfirm before assuming the IR LED is broken.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720

# Loaded from local copies (next to this script) instead of cv2.data.haarcascades,
# because that path contains non-ASCII characters (D:\工业设计\...) which OpenCV's
# C++ FileStorage reader fails to open on Windows.
_CASCADE_DIR = os.path.dirname(os.path.abspath(__file__))
face_cascade = cv2.CascadeClassifier(os.path.join(_CASCADE_DIR, "haarcascade_frontalface_default.xml"))
eye_cascade = cv2.CascadeClassifier(os.path.join(_CASCADE_DIR, "haarcascade_eye.xml"))

def detect_eye(gray_frame):
    """Returns (x, y, w, h) of one eye ROI in full-frame coordinates, or None."""
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    if len(faces) == 0:
        return None
    # use the largest detected face
    fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    face_roi = gray_frame[fy:fy + fh, fx:fx + fw]
    eyes = eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=8, minSize=(20, 20))
    if len(eyes) == 0:
        return None
    ex, ey, ew, eh = max(eyes, key=lambda e: e[2] * e[3])
    return (fx + ex, fy + ey, ew, eh)

def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Failed to open camera.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    print("Controls: 'm' manual ROI select | 's' save current auto ROI | 'q' quit")

    saved_count = 0
    last_roi = None
    auto_detect_attempts = 0
    auto_detect_hits = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        auto_detect_attempts += 1
        roi = detect_eye(gray)
        display = frame.copy()

        if roi is not None:
            auto_detect_hits += 1
            x, y, w, h = roi
            last_roi = roi
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            eye_crop = gray[y:y + h, x:x + w]
            cv2.imshow("Eye ROI", eye_crop)
        else:
            cv2.putText(display, "No auto eye detected - press 'm' for manual ROI",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        hit_rate = 100.0 * auto_detect_hits / auto_detect_attempts
        cv2.putText(display, f"Auto-detect hit rate: {hit_rate:.1f}% ({auto_detect_hits}/{auto_detect_attempts})",
                    (20, HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow("Original frame", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('m'):
            print("Manual mode: drag a box around one eye, press ENTER/SPACE to confirm, 'c' to cancel.")
            r = cv2.selectROI("Original frame", frame, showCrosshair=True)
            cv2.destroyWindow("ROI selector")
            x, y, w, h = r
            if w > 0 and h > 0:
                last_roi = (x, y, w, h)
                eye_crop = gray[y:y + h, x:x + w]
                fname = os.path.join(EYE_DIR, f"eye_manual_{int(time.time()*1000)}.png")
                cv2.imwrite(fname, eye_crop)
                saved_count += 1
                print(f"  Saved manual ROI: {fname}")
        elif key == ord('s'):
            if last_roi is not None:
                x, y, w, h = last_roi
                eye_crop = gray[y:y + h, x:x + w]
                fname = os.path.join(EYE_DIR, f"eye_auto_{int(time.time()*1000)}.png")
                cv2.imwrite(fname, eye_crop)
                saved_count += 1
                print(f"  Saved auto ROI: {fname}")
            else:
                print("  No ROI available to save yet.")

    cap.release()
    cv2.destroyAllWindows()

    print(f"\nSession summary:")
    print(f"  Auto-detect attempts: {auto_detect_attempts}")
    print(f"  Auto-detect hits: {auto_detect_hits} ({100.0*auto_detect_hits/max(1,auto_detect_attempts):.1f}%)")
    print(f"  ROI crops saved: {saved_count}")

if __name__ == "__main__":
    main()
