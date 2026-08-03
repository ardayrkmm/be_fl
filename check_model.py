import tensorflow as tf

class CustomLSTM(tf.keras.layers.LSTM):
    def __init__(self, *args, **kwargs):
        kwargs.pop("time_major", None)
        super().__init__(*args, **kwargs)

model = tf.keras.models.load_model('./lstm/coba_rabu_23/pose_model_lstm1.h5', compile=False, custom_objects={'LSTM': CustomLSTM})
print('EXPECTED SHAPE:', model.input_shape)
