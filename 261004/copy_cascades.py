import shutil
import os

SRC_DIR = r"D:\工业设计\Lib\site-packages\cv2\data"
DST_DIR = os.path.dirname(os.path.abspath(__file__))

files = ["haarcascade_frontalface_default.xml", "haarcascade_eye.xml"]
for f in files:
    src = os.path.join(SRC_DIR, f)
    dst = os.path.join(DST_DIR, f)
    shutil.copyfile(src, dst)
    print(f"Copied {f} -> {dst}")
