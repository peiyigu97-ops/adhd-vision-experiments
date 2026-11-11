"""
Sync script: mirrors the OV9281_test project (code + data) into the portfolio
course folder, leaving the original working directory untouched.

Run this after each stage to keep 261004 folder up to date.
"""
import shutil
import os

SRC = r"C:\Users\34659\OneDrive\Desktop\OV9281_test"
DST = r"D:\Homework\作品集\课程\261004"

def main():
    os.makedirs(DST, exist_ok=True)
    for item in os.listdir(SRC):
        s = os.path.join(SRC, item)
        d = os.path.join(DST, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    print(f"Synced {SRC} -> {DST}")

if __name__ == "__main__":
    main()
