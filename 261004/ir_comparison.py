"""
STEP 6b: IR illumination before/after comparison test.

Now that an 850nm IR LED has arrived, this script captures two sets of
10 static eye-region frames -- one with the IR LED OFF (ambient light only,
same condition as Stage 4/6), one with the IR LED ON -- under otherwise
identical head position/camera settings, and compares image quality metrics
side by side.

This answers one question only: "did adding IR illumination measurably
improve image quality (brightness, contrast, pupil-iris separability), or
not?" It does NOT re-run pupil detection yet -- that's STEP 6c, done only
after this comparison confirms the IR light is actually helping.

Usage: run this script, follow the on-screen prompts. It will pause and
wait for Enter before each capture batch so you have time to turn the LED
off/on between them.

--- Fix after 2 failed attempts ---
Attempt 1 was invalid: head position changed between the OFF and ON batch
(different scene content entirely), so brightness/contrast deltas were
meaningless.

Attempt 2 kept head position fixed, but produced a near-black ON image
(mean brightness 5.14) even though the LED was lit. Root cause: the
camera's auto-exposure reacted to the IR LED's point-source brightness
(likely visible directly or near-directly to the lens, or reflecting off
something close to it) by slamming exposure/gain down, which then
underexposed the actual eye region instead of illuminating it usefully.

This version fixes that by forcing a FIXED exposure/gain (auto-exposure
disabled) that is set once during IR-OFF conditions and kept identical for
both captures, so any brightness/contrast difference between OFF and ON is
caused by the LED's actual illumination, not by the camera's auto-exposure
algorithm reacting differently to each scene.
"""
import cv2
import os
import time
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
IR_TEST_DIR = os.path.join(BASE, "data", "ir_test")
OFF_DIR = os.path.join(IR_TEST_DIR, "ir_off")
ON_DIR = os.path.join(IR_TEST_DIR, "ir_on")
for d in [OFF_DIR, ON_DIR]:
    os.makedirs(d, exist_ok=True)

# Re-verified 2026-10-08 via identify_camera.py: index mapping had flipped
# (was 1=OV9281 on 2026-10-04, now 0=OV9281) after a USB re-enumeration event.
# If captures look wrong (unexpectedly dark, or colored instead of monochrome),
# rerun identify_camera.py to reconfirm before assuming the IR LED is broken.
CAMERA_INDEX = 0
WIDTH, HEIGHT = 1280, 720


def capture_batch(cap, out_dir, n=10):
    saved = 0
    attempts = 0
    while saved < n and attempts < 40:
        ret, frame = cap.read()
        attempts += 1
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(os.path.join(out_dir, f"frame_{saved:02d}.png"), gray)
        saved += 1
        time.sleep(0.15)
    return saved


def analyze_dir(d):
    files = sorted(f for f in os.listdir(d) if f.endswith(".png"))
    means, stds, sats = [], [], []
    for f in files:
        img = cv2.imread(os.path.join(d, f), cv2.IMREAD_GRAYSCALE)
        means.append(float(np.mean(img)))
        stds.append(float(np.std(img)))
        sat_pct = 100.0 * (np.sum(img == 0) + np.sum(img == 255)) / img.size
        sats.append(sat_pct)
    return {
        "n": len(files),
        "mean_brightness": round(float(np.mean(means)), 2) if means else None,
        "mean_std": round(float(np.mean(stds)), 2) if stds else None,
        "mean_saturated_pct": round(float(np.mean(sats)), 3) if sats else None,
    }


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Failed to open camera (index 1). Check camera is free (close other apps).")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    for _ in range(10):
        cap.read()  # warm up

    print("=" * 60)
    print("IR illumination before/after comparison")
    print("=" * 60)
    print("\nBEFORE YOU START -- check LED placement:")
    print("  The LED should point AT YOUR EYE, not toward the camera lens.")
    print("  If the camera can see the LED's bare light-emitting point directly")
    print("  (or a close reflection of it), auto-exposure reacts to that bright")
    print("  point instead of the eye, which is what caused the previous")
    print("  near-black result. Reposition so the lens does not look at the LED.")
    print("\nKeep your head/eye in the same position for both captures.")
    print("Position one eye in frame as you did in Stage 5 (eye_roi.py).")

    input("\nStep 1: Make sure the IR LED is OFF. Press Enter to lock exposure and capture 10 frames...")

    # Lock exposure/gain under IR-OFF (ambient) conditions, then keep those
    # exact settings for both batches. CAP_PROP_AUTO_EXPOSURE semantics are
    # backend/driver-dependent on Windows DSHOW: 0.25 = auto, 0.75 (or 1) =
    # manual on many UVC drivers. We read back whatever the driver settled on
    # under auto mode first, then switch to manual using that value, so we
    # are not guessing a fixed exposure blindly.
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)  # attempt to request manual mode
    locked_exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
    locked_gain = cap.get(cv2.CAP_PROP_GAIN)
    cap.set(cv2.CAP_PROP_EXPOSURE, locked_exposure)
    if locked_gain not in (-1.0, 0.0):
        cap.set(cv2.CAP_PROP_GAIN, locked_gain)
    print(f"  Locked exposure={locked_exposure}, gain={locked_gain} for both captures.")

    n_off = capture_batch(cap, OFF_DIR)
    print(f"  Captured {n_off} frames (IR OFF) -> {OFF_DIR}")

    input("\nStep 2: Turn the IR LED ON now. Press Enter to capture 10 frames (exposure stays locked)...")
    n_on = capture_batch(cap, ON_DIR)
    print(f"  Captured {n_on} frames (IR ON) -> {ON_DIR}")

    cap.release()

    stats_off = analyze_dir(OFF_DIR)
    stats_on = analyze_dir(ON_DIR)

    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)
    print(f"{'Metric':<25}{'IR OFF':<15}{'IR ON':<15}{'Change'}")
    for key, label in [("mean_brightness", "Mean brightness"),
                        ("mean_std", "Std dev (contrast)"),
                        ("mean_saturated_pct", "Saturated px %")]:
        off_v = stats_off[key]
        on_v = stats_on[key]
        delta = round(on_v - off_v, 2) if (off_v is not None and on_v is not None) else "N/A"
        print(f"{label:<25}{off_v!s:<15}{on_v!s:<15}{delta}")

    print("\nInterpretation:")
    if stats_on["mean_brightness"] and stats_off["mean_brightness"]:
        if stats_on["mean_brightness"] > stats_off["mean_brightness"] * 1.1:
            print("  Brightness increased noticeably with IR ON -- the LED is")
            print("  measurably contributing light the sensor picks up.")
        else:
            print("  Brightness did NOT increase much, even with exposure locked.")
            print("  Possible causes now that auto-exposure is ruled out:")
            print("  - LED may be too far/weak/misaligned (not actually illuminating the eye)")
            print("  - LED driver/circuit not actually powered")
            print("  - LED pointed at the lens rather than the eye (check the raw ON images")
            print("    visually for a bright point/glare rather than illuminated eye tissue)")
    print("\nThis script only compares image quality -- it does NOT confirm pupil")
    print("detection improved. Run pupil_detection_ir.py next (Stage 6c) to check that.")

if __name__ == "__main__":
    main()
