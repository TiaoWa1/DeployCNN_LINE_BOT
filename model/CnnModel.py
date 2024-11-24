import tensorflow as tf
import gc
from keras.models import load_model,Sequential
from keras.backend import clear_session

# 設置 tensorflow 動態取用顯存
config = tf.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
session = tf.compat.v1.Session(config=config)
tf.compat.v1.keras.backend.set_session(session)

def Load_CnnModel():    
    model = load_model("./model/Animal_faces_CNN.h5")
    return model

def Clear_model(Model_want_to_clear):
    del Model_want_to_clear
    clear_session()
    tf.compat.v1.reset_default_graph()
    gc.collect()