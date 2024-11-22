import tensorflow as tf
from keras.models import load_model,Sequential

def Load_CnnModel():
    model = load_model("./model/Animal_faces_CNN.h5")
    return model