import cv2
import os

print(cv2.__version__)
print(cv2.data.haarcascades)
print(os.listdir(cv2.data.haarcascades)[:5])
