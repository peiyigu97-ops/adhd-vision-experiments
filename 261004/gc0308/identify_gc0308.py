"""
GC0308 module - Step 1: device identification.

Plugging in a new USB camera can shift existing index assignments (this
already happened once with OV9281, see main experiment_report.md section 7a).
So this script re-enumerates ALL indices 0-4 fresh, rather than assuming the
new device lands at any particular index.

For each index that opens, saves one frame so the device can be identified
visually (resolution, color vs monochrome, FOV, IR glow pattern if any).
"""
"""
GC0308 module - Step 1: device identification.

Plugging in a new USB camera can shift existing index assignments (this
already happened once with OV9281, see main experiment_report.md section 7a).
So this script re-enumerates ALL indices 0-4 fresh, rather than assuming the
new device lands at any particular index.

For each index that opens, saves one frame so the device can be identified
visually (resolution, color vs monochrome, FOV, IR glow pattern if any).

Fixed 2026-11-04: this script used cv2.imwrite() directly, which silently
fails (returns False, no exception) on non-ASCII Windows paths -- and this
whole project tree lives under 作品集/课程/... Every other script in this
project that writes images already works around this (see
compare_algorithms.py / run_ellseg_inference.py's imwrite_unicode()), but
this particular file was apparently never updated to match and nobody
noticed because the old print statement didn't check cv2.imwrite's return
value -- it printed "saved ..." unconditionally, so the failure was
invisible until a user actually went looking for the files.
"""
import cv2
import numpy as np
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def imwrite_unicode(path, img):
    ext = os.path.splitext(path)[1]
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


print("=" * 60)
print("Enumerating camera indices 0-4 (DSHOW backend)")
print("=" * 60)

found = []
for idx in range(5):
    cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print(f"  index {idx}: not opened")
        continue
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    for _ in range(10):
        cap.read()  # warm up
    ret, frame = cap.read()
    if ret:
        fname = os.path.join(OUT_DIR, f"identify_index_{idx}.png")
        ok = imwrite_unicode(fname, frame)
        if ok:
            print(f"  index {idx}: OPENED, default {w}x{h}, saved {fname}, shape={frame.shape}")
            found.append(idx)
        else:
            print(f"  index {idx}: OPENED but FAILED TO WRITE {fname} -- check disk space/permissions, "
                  f"this is not the Chinese-path bug (that's already worked around above)")
    else:
        print(f"  index {idx}: opened but failed to read a frame")
    cap.release()

print(f"\nIndices that opened: {found}")
print("Visually inspect the saved identify_index_*.png files to determine")
print("which index is the GC0308 module (look for: small sensor FOV, IR glow")
print("or monochrome/greenish tint characteristic of cheap CMOS + IR LED combos)")
print("and which (if any) indices correspond to OV9281 / Integrated Camera.")
