import cv2
import numpy as np

def process(file_path):
    img = [cv2.resize(cv2.imread(file_path),(128, 128)) for i in file_path]
    img = (np.array(img).astype('float32'))/255.0
    return img