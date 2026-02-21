from flask import request
from flask_socketio import emit
from extensions import socketio
import numpy as np
import tensorflow as tf
import time
import os

# --- MODEL CONFIG ---
MODEL_PATH = "pose_model_lstm_lutut.h5" 
LABELS_PATH = "labels_lstm_lutut.txt"
SEQ_LEN = 15
FEATURE_COUNT = 132

# --- GLOBAL STATE ---
model = None
labels = []
sessions = {} # {sid: {'buffer': []}}

# Custom LSTM to handle Keras 2 -> 3 mismatch (time_major arg)
class CustomLSTM(tf.keras.layers.LSTM):
    def __init__(self, *args, **kwargs):
        # Remove the incompatible argument if present
        kwargs.pop('time_major', None)
        super().__init__(*args, **kwargs)

def load_pose_model():
    global model, labels
    try:
        print(f"🔧 [PoseController] Loading model: {MODEL_PATH}...")
        # Use CustomLSTM to ignore 'time_major'
        model = tf.keras.models.load_model(
            MODEL_PATH, 
            compile=False, 
            custom_objects={'LSTM': CustomLSTM}
        )
        print("✅ [PoseController] Keras Model Loaded Successfully")
        
        if os.path.exists(LABELS_PATH):
            with open(LABELS_PATH, 'r') as f:
                labels = [line.strip() for line in f.readlines()]
            print(f"✅ [PoseController] Labels Loaded: {labels}")
        else:
            print(f"⚠️ [PoseController] Labels file not found at {LABELS_PATH}")
            
    except Exception as e:
        print(f"❌ [PoseController] Error loading model: {e}")

# Load on module import (or can be called from app factory)
load_pose_model()

# --- EVENTS ---

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    sessions[sid] = {'buffer': []}
    print(f"🔌 [PoseController] Client connected: {sid}")
    emit('server_status', {'status': 'ready', 'type': 'keras_lstm'})

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in sessions:
        del sessions[sid]
    print(f"❌ [PoseController] Client disconnected: {sid}")


# --- GLOBAL STATE UPDATE ---
# sessions[sid] sekarang menyimpan buffer, id_latihan, dan counter
sessions = {} 

@socketio.on('start_session')
def handle_start_session(data):
    sid = request.sid
    id_latihan = data.get('id_latihan')
    sessions[sid] = {
    'buffer': [],
    'stats': {'benar': 0, 'salah': 0},
    'was_valid': False,
    'hold_start_time': None,
    'hold_completed': False
}
    print(f"🚀 [Session] User {sid} mulai latihan: {id_latihan}")

@socketio.on('send_pose_data')
def handle_pose_data(data):
    VALID_THRESHOLD = 0.7
    HOLD_DURATION = 3  
    sid = request.sid
    if sid not in sessions: return

    session = sessions[sid]
    buffer = session['buffer']
    landmarks = data.get('landmarks')

    if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
        return

    # 1. Push to Buffer
    buffer.append(landmarks)
    if len(buffer) > SEQ_LEN:
        buffer.pop(0)
        
    # 2. Inference
    if len(buffer) == SEQ_LEN and model is not None:
        try:
            input_tensor = np.array([buffer], dtype=np.float32)
            prediction = model.predict(input_tensor, verbose=0)
            
            max_idx = np.argmax(prediction[0])
            confidence = float(prediction[0][max_idx])
            raw_label = labels[max_idx] if max_idx < len(labels) else "Unknown"

            # 🔥 LOGIKA PEMBERSIHAN LABEL (Agar match dengan nama latihan di Flutter)
            # Contoh: "lying_leg" -> "Lying Leg"
            clean_label = raw_label.replace('_', ' ').title()

            # 🔥 LOGIKA FEEDBACK & COUNTER SEMENTARA
            feedback = "Posisi Benar"
            color = "#00FF00"
            is_valid = confidence >= VALID_THRESHOLD
            current_time = time.time()

            if is_valid:
                if not session['was_valid']:
                    # baru masuk zona benar
                    session['hold_start_time'] = current_time
                    session['hold_completed'] = False

                # cek apakah sudah cukup lama
                if (
                    session['hold_start_time'] is not None and
                    not session['hold_completed'] and
                    current_time - session['hold_start_time'] >= HOLD_DURATION
                ):
                    session['stats']['benar'] += 1
                    session['hold_completed'] = True

            else:
                # reset kalau keluar pose
                session['hold_start_time'] = None
                session['hold_completed'] = False

            session['was_valid'] = is_valid

            # Kirim respon ke Flutter
            emit('inference_result', {
                "label": clean_label, # Digunakan Flutter untuk: if(label == currentExercise) rep++
                "confidence": confidence,
                "feedback": feedback,
                "color": color,
                "is_valid": is_valid
            })
            
        except Exception as e:
            print(f"❌ Inference Error: {e}")

@socketio.on('end_exercise')
def handle_end_exercise():
    """Event saat user klik 'Selesai' di Flutter untuk ambil ringkasan data"""
    sid = request.sid
    if sid in sessions:
        stats = sessions[sid]['stats']
        # Kirim ringkasan agar Flutter bisa memanggil API /history
        emit('exercise_summary', {
            "total_benar": stats['benar'],
            "total_salah": stats['salah'],
            "akurasi": stats['benar'] / (stats['benar'] + stats['salah']) if (stats['benar'] + stats['salah']) > 0 else 0
        })
# socketio.on('send_pose_data')
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         sessions[sid] = {'buffer': []}

#     buffer = sessions[sid]['buffer']

#     # 🔥 AMBIL LIST DARI DICT
#     landmarks = data.get('landmarks')

#     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
#         print(f"⚠️ [PoseController] Invalid data format from {sid}: {type(landmarks)}")
#         return


#     # Debug Log (Throttled)
#     if len(buffer) == 0:
#         print(f"📥 [PoseController] Received valid pose data from {sid}") 
#     pass 

#     # 2. Buffer
#     buffer.append(landmarks)
    
#     # 3. Slide
#     if len(buffer) > SEQ_LEN:
#         buffer.pop(0)
        
#     # 4. Inference
#     if len(buffer) == SEQ_LEN and model is not None:
#         try:
#             # Input: (1, 15, 132)
#             input_tensor = np.array([buffer], dtype=np.float32)
            
#             # Predict
#             prediction = model.predict(input_tensor, verbose=0)
            
#             # Process
#             max_idx = np.argmax(prediction[0])
#             confidence = float(prediction[0][max_idx])
#             label = labels[max_idx] if max_idx < len(labels) else "Unknown"
            
#             print(f"🧠 [Inference] {label} ({confidence:.2f})")

#             # Feedback Logic
#             feedback = "Sempurna!"
#             color = "#00FF00"
            
#             if confidence < 0.5:
#                 feedback = "Salah Gerakan / Posisi"
#                 color = "#FF0000"
#             elif confidence < 0.8:
#                 feedback = "Sedikit lagi..."
#                 color = "#FFFF00"

#             response = {
#                 "label": label,
#                 "confidence": confidence,
#                 "feedback": feedback,
#                 "color": color
#             }
            
#             emit('inference_result', response)
            
#         except Exception as e:
#             print(f"❌ [PoseController] Inference Error: {e}")
