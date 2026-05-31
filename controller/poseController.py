# # from flask import request
# # from flask_socketio import emit
# # from extensions import socketio
# # import numpy as np
# # import tensorflow as tf
# # import time
# # import os

# # # --- MODEL CONFIG ---
# # MODEL_PATH = "pose_model_lstm_lutut.h5" 
# # LABELS_PATH = "labels_lstm_lutut.txt"
# # SEQ_LEN = 15
# # FEATURE_COUNT = 132

# # # --- GLOBAL STATE ---
# # # model = None
# # # labels = []
# # # sessions = {} # {sid: {'buffer': []}}
# # MODEL_CONFIG = {
# #     "LUTUT": {
# #         "model_path": "pose_model_lstm_lutut.h5",
# #         "labels_path": "labels_lstm_lutut.txt"
# #     },
# #     "BAHU": {
# #         "model_path": "pose_model_lstm_bahu.h5",
# #         "labels_path": "labels_lstm_bahu.txt"
# #     }
# # }

# # models = {}   # {"LUTUT": model_object, "BAHU": model_object}
# # labels_map = {}  # {"LUTUT": [...], "BAHU": [...]}

# # # Custom LSTM to handle Keras 2 -> 3 mismatch (time_major arg)
# # class CustomLSTM(tf.keras.layers.LSTM):
# #     def __init__(self, *args, **kwargs):
# #         # Remove the incompatible argument if present
# #         kwargs.pop('time_major', None)
# #         super().__init__(*args, **kwargs)

# # def load_all_models():
# #     global models, labels_map
    
# #     for bagian, config in MODEL_CONFIG.items():
# #         try:
# #             print(f"🔧 Loading {bagian} model...")
            
# #             model = tf.keras.models.load_model(
# #                 config["model_path"],
# #                 compile=False,
# #                 custom_objects={'LSTM': CustomLSTM}
# #             )
            
# #             models[bagian] = model
            
# #             with open(config["labels_path"], 'r') as f:
# #                 labels_map[bagian] = [line.strip() for line in f.readlines()]
                
# #             print(f"[SUCCESS] {bagian} model loaded")
            
# #         except Exception as e:
# #             print(f"[ERROR] Error loading {bagian}: {e}")

# # # Load on module import (or can be called from app factory)
# # load_all_models()

# # # --- EVENTS ---

# # @socketio.on('connect')
# # def handle_connect():
# #     sid = request.sid
# #     sessions[sid] = {'buffer': []}
# #     print(f"[CONNECT] [PoseController] Client connected: {sid}")
# #     emit('server_status', {'status': 'ready', 'type': 'keras_lstm'})

# # @socketio.on('disconnect')
# # def handle_disconnect():
# #     sid = request.sid
# #     if sid in sessions:
# #         del sessions[sid]
# #     print(f"[ERROR] [PoseController] Client disconnected: {sid}")


# # # --- GLOBAL STATE UPDATE ---
# # # sessions[sid] sekarang menyimpan buffer, id_latihan, dan counter
# # sessions = {} 

# # @socketio.on('start_session')
# # def handle_start_session(data):
# #     sid = request.sid
# #     id_latihan = data.get('id_latihan')
# #     sessions[sid] = {
# #     'buffer': [],
# #     'stats': {'benar': 0, 'salah': 0},
# #     'was_valid': False,
# #     'hold_start_time': None,
# #     'hold_completed': False
# # }
# #     print(f"[START] [Session] User {sid} mulai latihan: {id_latihan}")

# # @socketio.on('send_pose_data')
# # def handle_pose_data(data):
# #     VALID_THRESHOLD = 0.7
# #     HOLD_DURATION = 3  
# #     sid = request.sid
# #     if sid not in sessions: return

# #     session = sessions[sid]
# #     buffer = session['buffer']
# #     landmarks = data.get('landmarks')

# #     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
# #         return

# #     # 1. Push to Buffer
# #     buffer.append(landmarks)
# #     if len(buffer) > SEQ_LEN:
# #         buffer.pop(0)
        
# #     # 2. Inference
# #     if len(buffer) == SEQ_LEN and model is not None:
# #         try:
# #             input_tensor = np.array([buffer], dtype=np.float32)
# #             prediction = model.predict(input_tensor, verbose=0)
            
# #             max_idx = np.argmax(prediction[0])
# #             confidence = float(prediction[0][max_idx])
# #             raw_label = labels[max_idx] if max_idx < len(labels) else "Unknown"

# #             # 🔥 LOGIKA PEMBERSIHAN LABEL (Agar match dengan nama latihan di Flutter)
# #             # Contoh: "lying_leg" -> "Lying Leg"
# #             clean_label = raw_label.replace('_', ' ').title()

# #             # 🔥 LOGIKA FEEDBACK & COUNTER SEMENTARA
# #             feedback = "Posisi Benar"
# #             color = "#00FF00"
# #             is_valid = confidence >= VALID_THRESHOLD
# #             current_time = time.time()

# #             if is_valid:
# #                 if not session['was_valid']:
# #                     # baru masuk zona benar
# #                     session['hold_start_time'] = current_time
# #                     session['hold_completed'] = False

# #                 # cek apakah sudah cukup lama
# #                 if (
# #                     session['hold_start_time'] is not None and
# #                     not session['hold_completed'] and
# #                     current_time - session['hold_start_time'] >= HOLD_DURATION
# #                 ):
# #                     session['stats']['benar'] += 1
# #                     session['hold_completed'] = True

# #             else:
# #                 # reset kalau keluar pose
# #                 session['hold_start_time'] = None
# #                 session['hold_completed'] = False

# #             session['was_valid'] = is_valid

# #             # Kirim respon ke Flutter
# #             emit('inference_result', {
# #                 "label": clean_label, # Digunakan Flutter untuk: if(label == currentExercise) rep++
# #                 "confidence": confidence,
# #                 "feedback": feedback,
# #                 "color": color,
# #                 "is_valid": is_valid
# #             })
            
# #         except Exception as e:
# #             print(f"[ERROR] Inference Error: {e}")

# # @socketio.on('end_exercise')
# # def handle_end_exercise():
# #     """Event saat user klik 'Selesai' di Flutter untuk ambil ringkasan data"""
# #     sid = request.sid
    
# #     # 1. Pastikan sid ada di sessions DAN key 'stats' sudah dibuat
# #     if sid in sessions and 'stats' in sessions[sid]:
# #         stats = sessions[sid]['stats']
# #         total_gerakan = stats['benar'] + stats['salah']
# #         akurasi = stats['benar'] / total_gerakan if total_gerakan > 0 else 0
        
# #         # Kirim ringkasan agar Flutter bisa memanggil API /history
# #         emit('exercise_summary', {
# #             "total_benar": stats['benar'],
# #             "total_salah": stats['salah'],
# #             "akurasi": akurasi
# #         })
# #     else:
# #         # 2. Jika tidak ada stats (karena belum start_session / error), kembalikan nilai 0
# #         print(f"⚠️ [PoseController] Peringatan: Data 'stats' tidak ditemukan untuk SID {sid} saat end_exercise")
# #         emit('exercise_summary', {
# #             "total_benar": 0,
# #             "total_salah": 0,
# #             "akurasi": 0.0
# #         })

# # from flask import request
# # from flask_socketio import emit
# # from extensions import socketio
# # from models import Latihan
# # import numpy as np
# # import tensorflow as tf
# # import time

# # # ===============================
# # # CONFIG
# # # ===============================

# # SEQ_LEN = 15
# # FEATURE_COUNT = 132
# # VALID_THRESHOLD = 0.7
# # HOLD_DURATION = 3  # seconds

# # MODEL_CONFIG = {
# #     "LUTUT": {
# #         "model_path": "./lstm/pose_model_lstm_lutut.h5",
# #         "labels_path": "./lstm/labels_lstm_lutut.txt"
# #     },
# #     "BAHU": {
# #         "model_path": "./lstm/pose_model_lstm_bahu.h5",
# #         "labels_path": "./lstm/labels_lstm_bahu.txt"
# #     }
# # }

# # models = {}
# # labels_map = {}
# # sessions = {}

# # # ===============================
# # # FIX KERAS 2 → 3
# # # ===============================

# # class CustomLSTM(tf.keras.layers.LSTM):
# #     def __init__(self, *args, **kwargs):
# #         kwargs.pop('time_major', None)
# #         super().__init__(*args, **kwargs)

# # # ===============================
# # # LOAD ALL MODELS
# # # ===============================

# # def load_all_models():
# #     for key, config in MODEL_CONFIG.items():
# #         try:
# #             print(f"🔧 Loading model {key}")

# #             model = tf.keras.models.load_model(
# #                 config["model_path"],
# #                 compile=False,
# #                 custom_objects={'LSTM': CustomLSTM}
# #             )

# #             models[key] = model

# #             with open(config["labels_path"], "r") as f:
# #                 labels_map[key] = [line.strip() for line in f.readlines()]

# #             print(f"[SUCCESS] Model {key} loaded")

# #         except Exception as e:
# #             print(f"[ERROR] Failed loading {key}: {e}")

# # load_all_models()

# # # ===============================
# # # CONNECT
# # # ===============================

# # @socketio.on("connect")
# # def handle_connect():
# #     sid = request.sid

# #     sessions[sid] = {
# #         "buffer": [],
# #         "model_key": None,
# #         "expected_label": None,
# #         "stats": {"benar": 0, "salah": 0},
# #         "was_valid": False,
# #         "hold_start_time": None,
# #         "hold_completed": False,
# #         "start_time": None
# #     }

# #     print(f"[CONNECT] Client connected: {sid}")
# #     emit("server_status", {"status": "ready"}, room=sid)

# # # ===============================
# # # DISCONNECT
# # # ===============================

# # @socketio.on("disconnect")
# # def handle_disconnect():
# #     sid = request.sid
# #     sessions.pop(sid, None)
# #     print(f"[ERROR] Client disconnected: {sid}")

# # # ===============================
# # # START SESSION
# # # ===============================

# # @socketio.on("start_session")
# # def handle_start_session(data):
# #     sid = request.sid
# #     id_latihan = data.get("id_latihan")

# #     session = sessions.get(sid)
# #     if not session:
# #         return

# #     latihan = Latihan.query.filter_by(id_latihan=id_latihan).first()
# #     if not latihan:
# #         emit("error", {"message": "Latihan tidak ditemukan"}, room=sid)
# #         return

# #     model_key = latihan.bagian_tubuh.model_key

# #     if model_key not in models:
# #         emit("error", {"message": "Model tidak tersedia"}, room=sid)
# #         return

# #     # Reset session state
# #     session.update({
# #         "buffer": [],
# #         "model_key": model_key,
# #         "expected_label": latihan.nama_latihan,
# #         "stats": {"benar": 0, "salah": 0},
# #         "was_valid": False,
# #         "hold_start_time": None,
# #         "hold_completed": False,
# #         "start_time": time.time()
# #     })

# #     emit("session_started", {
# #         "latihan": latihan.nama_latihan
# #     }, room=sid)

# #     print(f"▶ Session started | {sid} | {latihan.nama_latihan}")

# # # ===============================
# # # RECEIVE POSE DATA
# # # ===============================

# # @socketio.on("send_pose_data")
# # def handle_pose_data(data):
# #     sid = request.sid
# #     session = sessions.get(sid)

# #     if not session or not session.get("model_key"):
# #         return

# #     landmarks = data.get("landmarks")

# #     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
# #         return

# #     buffer = session["buffer"]
# #     buffer.append(landmarks)

# #     if len(buffer) > SEQ_LEN:
# #         buffer.pop(0)

# #     if len(buffer) != SEQ_LEN:
# #         return

# #     model = models.get(session["model_key"])
# #     labels = labels_map.get(session["model_key"], [])

# #     if model is None:
# #         return

# #     try:
# #         input_tensor = np.array([buffer], dtype=np.float32)
# #         prediction = model.predict(input_tensor, verbose=0)

# #         max_idx = int(np.argmax(prediction[0]))
# #         confidence = float(prediction[0][max_idx])
# #         raw_label = labels[max_idx] if max_idx < len(labels) else "Unknown"
# #         clean_label = raw_label.replace("_", " ").title()

# #         is_valid = (
# #             confidence >= VALID_THRESHOLD and
# #             clean_label == session["expected_label"]
# #         )

# #         current_time = time.time()

# #         # ===============================
# #         # HOLD LOGIC
# #         # ===============================

# #         if is_valid:
# #             if not session["was_valid"]:
# #                 session["hold_start_time"] = current_time
# #                 session["hold_completed"] = False

# #             elif (
# #                 session["hold_start_time"] and
# #                 not session["hold_completed"] and
# #                 current_time - session["hold_start_time"] >= HOLD_DURATION
# #             ):
# #                 session["stats"]["benar"] += 1
# #                 session["hold_completed"] = True

# #         else:
# #             if session["was_valid"]:
# #                 session["stats"]["salah"] += 1

# #             session["hold_start_time"] = None
# #             session["hold_completed"] = False

# #         session["was_valid"] = is_valid

# #         emit("inference_result", {
# #             "predicted_label": clean_label,
# #             "confidence": confidence,
# #             "is_valid": is_valid,
# #             "repetition": session["stats"]["benar"],
# #             "salah": session["stats"]["salah"]
# #         }, room=sid)

# #     except Exception as e:
# #         print("[ERROR] Inference error:", e)

# # # ===============================
# # # END EXERCISE
# # # ===============================

# # @socketio.on("end_exercise")
# # def handle_end_exercise():
# #     sid = request.sid
# #     session = sessions.get(sid)

# #     if not session:
# #         return

# #     stats = session["stats"]
# #     total = stats["benar"] + stats["salah"]
# #     akurasi = stats["benar"] / total if total > 0 else 0

# #     duration = (
# #         time.time() - session["start_time"]
# #         if session["start_time"]
# #         else 0
# #     )

# #     emit("exercise_summary", {
# #         "jumlah_gerakan_benar": stats["benar"],
# #         "jumlah_gerakan_salah": stats["salah"],
# #         "akurasi_latihan": akurasi,
# #         "durasi_latihan": duration
# #     }, room=sid)

# #     # Reset ringan
# #     session.update({
# #         "buffer": [],
# #         "model_key": None,
# #         "expected_label": None,
# #         "was_valid": False,
# #         "hold_start_time": None,
# #         "hold_completed": False,
# #         "start_time": None
# #     })

# #     print(f"[STATS] Session ended | {sid} | Benar: {stats['benar']} | Salah: {stats['salah']}")
# # socketio.on('send_pose_data')
# # def handle_pose_data(data):
# #     sid = request.sid

# #     if sid not in sessions:
# #         sessions[sid] = {'buffer': []}

# #     buffer = sessions[sid]['buffer']

# #     # 🔥 AMBIL LIST DARI DICT
# #     landmarks = data.get('landmarks')

# #     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
# #         print(f"⚠️ [PoseController] Invalid data format from {sid}: {type(landmarks)}")
# #         return


# #     # Debug Log (Throttled)
# #     if len(buffer) == 0:
# #         print(f"📥 [PoseController] Received valid pose data from {sid}") 
# #     pass 

# #     # 2. Buffer
# #     buffer.append(landmarks)
    
# #     # 3. Slide
# #     if len(buffer) > SEQ_LEN:
# #         buffer.pop(0)
        
# #     # 4. Inference
# #     if len(buffer) == SEQ_LEN and model is not None:
# #         try:
# #             # Input: (1, 15, 132)
# #             input_tensor = np.array([buffer], dtype=np.float32)
            
# #             # Predict
# #             prediction = model.predict(input_tensor, verbose=0)
            
# #             # Process
# #             max_idx = np.argmax(prediction[0])
# #             confidence = float(prediction[0][max_idx])
# #             label = labels[max_idx] if max_idx < len(labels) else "Unknown"
            
# #             print(f"🧠 [Inference] {label} ({confidence:.2f})")

# #             # Feedback Logic
# #             feedback = "Sempurna!"
# #             color = "#00FF00"
            
# #             if confidence < 0.5:
# #                 feedback = "Salah Gerakan / Posisi"
# #                 color = "#FF0000"
# #             elif confidence < 0.8:
# #                 feedback = "Sedikit lagi..."
# #                 color = "#FFFF00"

# #             response = {
# #                 "label": label,
# #                 "confidence": confidence,
# #                 "feedback": feedback,
# #                 "color": color
# #             }
            
# #             emit('inference_result', response)
            
# #         except Exception as e:
# #             print(f"[ERROR] [PoseController] Inference Error: {e}")


# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import time
# import os
# import joblib

# # ===============================
# # CONFIG
# # ===============================
# # MODEL_PATH = "pose_model_lstm_fixed.keras"
# # LABELS_PATH = "labels.txt"
# # SCALER_PATH = "scaler.save"

# # SEQ_LEN = 15
# # FEATURE_COUNT = 132
# # VALID_THRESHOLD = 0.7
# # HOLD_DURATION = 3

# # # ===============================
# # # GLOBAL STATE
# # # ===============================
# # model = None
# # labels = []
# # scaler = None
# # sessions = {}

# # # ===============================
# # # FIX KERAS 2 -> 3 LSTM ISSUE
# # # ===============================
# # class CustomLSTM(tf.keras.layers.LSTM):
# #     def __init__(self, *args, **kwargs):
# #         kwargs.pop("time_major", None)
# #         super().__init__(*args, **kwargs)

# # # ===============================
# # # LOAD MODEL
# # # ===============================
# # def load_pose_model():
# #     global model, labels, scaler

# #     try:
# #         print("🔧 Loading LSTM Model...")
# #         model = tf.keras.models.load_model(
# #             MODEL_PATH,
# #             compile=False,
# #             custom_objects={"LSTM": CustomLSTM}
# #         )
# #         print("[SUCCESS] Model Loaded")

# #         if os.path.exists(LABELS_PATH):
# #             with open(LABELS_PATH, "r") as f:
# #                 labels.extend([line.strip() for line in f])
# #             print("[SUCCESS] Labels Loaded:", labels)

# #         if os.path.exists(SCALER_PATH):
# #             scaler = joblib.load(SCALER_PATH)
# #             print("[SUCCESS] Scaler Loaded")

# #     except Exception as e:
# #         print("[ERROR] Model Load Error:", e)

# # load_pose_model()

# # # ===============================
# # # SOCKET EVENTS
# # # ===============================

# # @socketio.on("connect")
# # def handle_connect():
# #     sid = request.sid
# #     sessions[sid] = {
# #         "buffer": [],
# #         "stats": {"benar": 0, "salah": 0},
# #         "was_valid": False,
# #         "hold_start_time": None,
# #         "hold_completed": False
# #     }

# #     print(f"[CONNECT] Client Connected: {sid}")
# #     emit("server_status", {"status": "ready"})


# # @socketio.on("disconnect")
# # def handle_disconnect():
# #     sid = request.sid
# #     sessions.pop(sid, None)
# #     print(f"[ERROR] Client Disconnected: {sid}")


# # # ===============================
# # # START SESSION
# # # ===============================
# # @socketio.on("start_session")
# # def handle_start_session(data):
# #     sid = request.sid
# #     if sid not in sessions:
# #         return

# #     sessions[sid]["stats"] = {"benar": 0, "salah": 0}
# #     sessions[sid]["buffer"] = []
# #     sessions[sid]["was_valid"] = False
# #     sessions[sid]["hold_start_time"] = None
# #     sessions[sid]["hold_completed"] = False

# #     print(f"[START] Session Started: {sid}")


# # # ===============================
# # # INFERENCE
# # # ===============================
# # @socketio.on("send_pose_data")
# # def handle_pose_data(data):

# #     sid = request.sid
# #     if sid not in sessions:
# #         return

# #     if model is None or scaler is None:
# #         return

# #     session = sessions[sid]
# #     buffer = session["buffer"]

# #     landmarks = data.get("landmarks")

# #     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
# #         return

# #     # ===============================
# #     # 1️⃣ PUSH TO BUFFER
# #     # ===============================
# #     buffer.append(landmarks)
# #     if len(buffer) > SEQ_LEN:
# #         buffer.pop(0)

# #     # ===============================
# #     # 2️⃣ INFERENCE WHEN FULL
# #     # ===============================
# #     if len(buffer) == SEQ_LEN:

# #         try:
# #             input_array = np.array(buffer, dtype=np.float32)

# #             # 🔥 APPLY SCALER (IDENTICAL TO TRAINING)
# #             reshaped = input_array.reshape(-1, FEATURE_COUNT)
# #             scaled = scaler.transform(reshaped)
# #             scaled = scaled.reshape(1, SEQ_LEN, FEATURE_COUNT)

# #             prediction = model.predict(scaled, verbose=0)

# #             max_idx = int(np.argmax(prediction[0]))
# #             confidence = float(prediction[0][max_idx])

# #             raw_label = labels[max_idx]
# #             clean_label = raw_label.replace("_", " ").title()

# #             # ===============================
# #             # HOLD LOGIC
# #             # ===============================
# #             is_valid = confidence >= VALID_THRESHOLD
# #             current_time = time.time()

# #             if is_valid:
# #                 if not session["was_valid"]:
# #                     session["hold_start_time"] = current_time
# #                     session["hold_completed"] = False

# #                 if (
# #                     session["hold_start_time"] is not None and
# #                     not session["hold_completed"] and
# #                     current_time - session["hold_start_time"] >= HOLD_DURATION
# #                 ):
# #                     session["stats"]["benar"] += 1
# #                     session["hold_completed"] = True

# #             else:
# #                 session["hold_start_time"] = None
# #                 session["hold_completed"] = False

# #             session["was_valid"] = is_valid

# #             emit("inference_result", {
# #                 "label": clean_label,
# #                 "confidence": confidence,
# #                 "is_valid": is_valid,
# #                 "total_benar": session["stats"]["benar"]
# #             })

# #         except Exception as e:
# #             print("[ERROR] Inference Error:", e)


# # # ===============================
# # # END EXERCISE
# # # ===============================
# # @socketio.on("end_exercise")
# # def handle_end_exercise():
# #     sid = request.sid

# #     if sid not in sessions:
# #         return

# #     stats = sessions[sid]["stats"]
# #     total = stats["benar"] + stats["salah"]
# #     accuracy = stats["benar"] / total if total > 0 else 0

# #     emit("exercise_summary", {
# #         "total_benar": stats["benar"],
# #         "total_salah": stats["salah"],
# #         "akurasi": accuracy
# #     })



# MODEL_PATH = "pose_model_lstm.h5" 
# LABELS_PATH = "labels_model.txt"
# SEQ_LEN = 20
# FEATURE_COUNT = 133

# # --- GLOBAL STATE ---
# model = None
# labels = []
# sessions = {} # {sid: {'buffer': []}}

# # Custom LSTM to handle Keras 2 -> 3 mismatch (time_major arg)
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         # Remove the incompatible argument if present
#         kwargs.pop('time_major', None)
#         super().__init__(*args, **kwargs)

# def load_pose_model():
#     global model, labels
#     try:
#         print(f"🔧 [PoseController] Loading model: {MODEL_PATH}...")
#         # Use CustomLSTM to ignore 'time_major'
#         model = tf.keras.models.load_model(
#             MODEL_PATH, 
#             compile=False, 
#             custom_objects={'LSTM': CustomLSTM}
#         )
#         print("[SUCCESS] [PoseController] Keras Model Loaded Successfully")
        
#         if os.path.exists(LABELS_PATH):
#             with open(LABELS_PATH, 'r') as f:
#                 labels = [line.strip() for line in f.readlines()]
#             print(f"[SUCCESS] [PoseController] Labels Loaded: {labels}")
#         else:
#             print(f"⚠️ [PoseController] Labels file not found at {LABELS_PATH}")
            
#     except Exception as e:
#         print(f"[ERROR] [PoseController] Error loading model: {e}")

# # Load on module import (or can be called from app factory)
# load_pose_model()

# # --- EVENTS ---

# @socketio.on('connect')
# def handle_connect():
#     sid = request.sid
#     sessions[sid] = {'buffer': []}
#     print(f"[CONNECT] [PoseController] Client connected: {sid}")
#     emit('server_status', {'status': 'ready', 'type': 'keras_lstm'})

# @socketio.on('disconnect')
# def handle_disconnect():
#     sid = request.sid
#     if sid in sessions:
#         del sessions[sid]
#     print(f"[ERROR] [PoseController] Client disconnected: {sid}")


# # --- GLOBAL STATE UPDATE ---
# # sessions[sid] sekarang menyimpan buffer, id_latihan, dan counter
# sessions = {} 

# @socketio.on('start_session')
# def handle_start_session(data):
#     sid = request.sid
#     id_latihan = data.get('id_latihan')
#     sessions[sid] = {
#     'buffer': [],
#     'stats': {'benar': 0, 'salah': 0},
#     'was_valid': False,
#     'hold_start_time': None,
#     'hold_completed': False
# }
#     print(f"[START] [Session] User {sid} mulai latihan: {id_latihan}")

# @socketio.on('send_pose_data')
# def handle_pose_data(data):
#     VALID_THRESHOLD = 0.7
#     HOLD_DURATION = 3  
#     sid = request.sid
#     if sid not in sessions: return

#     session = sessions[sid]
#     buffer = session['buffer']
#     landmarks = data.get('landmarks')

#     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
#         return

#     # 1. Push to Buffer
#     buffer.append(landmarks)
#     if len(buffer) > SEQ_LEN:
#         buffer.pop(0)
        
#     # 2. Inference
#     if len(buffer) == SEQ_LEN and model is not None:
#         try:
#             input_tensor = np.array([buffer], dtype=np.float32)
#             prediction = model.predict(input_tensor, verbose=0)
            
#             max_idx = np.argmax(prediction[0])
#             confidence = float(prediction[0][max_idx])
#             raw_label = labels[max_idx] if max_idx < len(labels) else "Unknown"

#             # 🔥 LOGIKA PEMBERSIHAN LABEL (Agar match dengan nama latihan di Flutter)
#             # Contoh: "lying_leg" -> "Lying Leg"
#             clean_label = raw_label.replace('_', ' ').title()

#             # 🔥 LOGIKA FEEDBACK & COUNTER SEMENTARA
#             feedback = "Posisi Benar"
#             color = "#00FF00"
#             is_valid = confidence >= VALID_THRESHOLD
#             current_time = time.time()

#             if is_valid:
#                 if not session['was_valid']:
#                     # baru masuk zona benar
#                     session['hold_start_time'] = current_time
#                     session['hold_completed'] = False

#                 # cek apakah sudah cukup lama
#                 if (
#                     session['hold_start_time'] is not None and
#                     not session['hold_completed'] and
#                     current_time - session['hold_start_time'] >= HOLD_DURATION
#                 ):
#                     session['stats']['benar'] += 1
#                     session['hold_completed'] = True

#             else:
#                 # reset kalau keluar pose
#                 session['hold_start_time'] = None
#                 session['hold_completed'] = False

#             session['was_valid'] = is_valid

#             # Kirim respon ke Flutter
#             emit('inference_result', {
#                 "label": clean_label, # Digunakan Flutter untuk: if(label == currentExercise) rep++
#                 "confidence": confidence,
#                 "feedback": feedback,
#                 "color": color,
#                 "is_valid": is_valid
#             })
            
#         except Exception as e:
#             print(f"[ERROR] Inference Error: {e}")

# @socketio.on('end_exercise')
# def handle_end_exercise():
#     """Event saat user klik 'Selesai' di Flutter untuk ambil ringkasan data"""
#     sid = request.sid
#     if sid in sessions:
#         stats = sessions[sid]['stats']
#         # Kirim ringkasan agar Flutter bisa memanggil API /history
#         emit('exercise_summary', {
#             "total_benar": stats['benar'],
#             "total_salah": stats['salah'],
#             "akurasi": stats['benar'] / (stats['benar'] + stats['salah']) if (stats['benar'] + stats['salah']) > 0 else 0
#         })


# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# from collections import deque, Counter

# # ===============================
# # CONFIG
# # ===============================
# MODEL_PATH = "pose_model_lstm.h5"
# LABELS_PATH = "labels_model.txt"

# SEQ_LEN = 20
# FEATURE_COUNT = 133

# VALID_THRESHOLD = 0.7
# STABILITY_WINDOW = 5   # jumlah prediksi untuk stabilisasi label

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []
# sessions = {}

# # ===============================
# # FIX LSTM
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         kwargs.pop('time_major', None)
#         super().__init__(*args, **kwargs)

# # ===============================
# # LOAD MODEL
# # ===============================
# def load_pose_model():
#     global model, labels
#     try:
#         print(f"🔧 Loading model: {MODEL_PATH}")

#         model = tf.keras.models.load_model(
#             MODEL_PATH,
#             compile=False,
#             custom_objects={'LSTM': CustomLSTM}
#         )

#         print("✅ Model loaded")

#         if os.path.exists(LABELS_PATH):
#             with open(LABELS_PATH, 'r') as f:
#                 labels = [line.strip() for line in f.readlines()]
#             print(f"✅ Labels: {labels}")

#     except Exception as e:
#         print(f"❌ Load error: {e}")

# load_pose_model()

# # ===============================
# # CONNECT
# # ===============================
# @socketio.on('connect')
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "prediction_history": deque(maxlen=STABILITY_WINDOW),
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": None
#     }

#     print(f"[CONNECT] {sid}")
#     emit("server_status", {"status": "ready"})

# # ===============================
# # DISCONNECT
# # ===============================
# @socketio.on('disconnect')
# def handle_disconnect():
#     sid = request.sid
#     sessions.pop(sid, None)
#     print(f"[DISCONNECT] {sid}")

# # ===============================
# # START SESSION
# # ===============================
# @socketio.on('start_session')
# def handle_start_session(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     expected = data.get("expected_label", "")

#     sessions[sid].update({
#         "buffer": [],
#         "prediction_history": deque(maxlen=STABILITY_WINDOW),
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": expected.lower().strip()
#     })

#     print(f"[START] {sid} target: {expected}")

# # ===============================
# # POSE DATA
# # ===============================
# @socketio.on('send_pose_data')
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     buffer = session["buffer"]

#     landmarks = data.get("landmarks")

#     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
#         return

#     # ===============================
#     # BUFFER
#     # ===============================
#     buffer.append(landmarks)
#     if len(buffer) > SEQ_LEN:
#         buffer.pop(0)

#     # ===============================
#     # INFERENCE
#     # ===============================
#     if len(buffer) == SEQ_LEN and model is not None:
#         try:
#             input_tensor = np.array([buffer], dtype=np.float32)
#             prediction = model.predict(input_tensor, verbose=0)

#             max_idx = int(np.argmax(prediction[0]))
#             confidence = float(prediction[0][max_idx])

#             raw_label = labels[max_idx] if max_idx < len(labels) else "unknown"
#             clean_label = raw_label.replace("_", " ").lower()

#             # ===============================
#             # STABILISASI LABEL
#             # ===============================
#             session["prediction_history"].append(clean_label)

#             stable_label = Counter(session["prediction_history"]).most_common(1)[0][0]

#             # ===============================
#             # VALIDATION
#             # ===============================
#             expected = session["expected_label"]

#             is_match = stable_label == expected
#             is_valid = confidence >= VALID_THRESHOLD

#             is_correct = is_match and is_valid

#             # ===============================
#             # UPDATE STATS
#             # ===============================
#             if is_correct:
#                 session["stats"]["benar"] += 1
#             else:
#                 session["stats"]["salah"] += 1

#             # ===============================
#             # EMIT
#             # ===============================
#             emit("inference_result", {
#                 "label": stable_label,
#                 "confidence": confidence,
#                 "is_valid": is_valid,
#                 "is_match": is_match,
#                 "is_correct": is_correct,
#                 "total_benar": session["stats"]["benar"],
#                 "total_salah": session["stats"]["salah"]
#             })

#         except Exception as e:
#             print("[ERROR]", e)

# # ===============================
# # END SESSION
# # ===============================
# @socketio.on('end_exercise')
# def handle_end_exercise():
#     sid = request.sid

#     if sid not in sessions:
#         return

#     stats = sessions[sid]["stats"]
#     total = stats["benar"] + stats["salah"]

#     accuracy = stats["benar"] / total if total > 0 else 0

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": accuracy
#     })

#     print(f"[SUMMARY] {sid} | Acc: {accuracy:.2f}")

# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# from collections import deque, Counter

# # ===============================
# # CONFIG
# # ===============================
# MODEL_PATH = "pose_model_lstm.h5"
# LABELS_PATH = "labels_model.txt"

# SEQ_LEN = 20
# FEATURE_COUNT = 133

# VALID_THRESHOLD = 0.7
# STABILITY_WINDOW = 5

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []
# sessions = {}

# # ===============================
# # FIX LSTM COMPATIBILITY
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         kwargs.pop("time_major", None)
#         super().__init__(*args, **kwargs)

# # ===============================
# # LOAD MODEL
# # ===============================
# def load_pose_model():
#     global model, labels

#     try:
#         print(f"🔧 Loading model: {MODEL_PATH}")

#         model = tf.keras.models.load_model(
#             MODEL_PATH,
#             compile=False,
#             custom_objects={"LSTM": CustomLSTM}
#         )

#         print("✅ Model loaded")

#         if os.path.exists(LABELS_PATH):
#             with open(LABELS_PATH, "r") as f:
#                 labels = [line.strip() for line in f.readlines()]
#             print(f"✅ Labels loaded: {len(labels)} classes")

#     except Exception as e:
#         print("❌ Model load error:", e)

# load_pose_model()

# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "prediction_history": deque(maxlen=STABILITY_WINDOW),
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": None
#     }

#     print(f"[CONNECT] {sid}")
#     emit("server_status", {"status": "ready"})

# # ===============================
# # DISCONNECT
# # ===============================
# @socketio.on("disconnect")
# def handle_disconnect():
#     sid = request.sid
#     sessions.pop(sid, None)
#     print(f"[DISCONNECT] {sid}")

# # ===============================
# # START SESSION
# # ===============================
# @socketio.on("start_session")
# def handle_start_session(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     expected = data.get("expected_label", "")

#     sessions[sid].update({
#         "buffer": [],
#         "prediction_history": deque(maxlen=STABILITY_WINDOW),
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": expected.lower().strip()
#     })

#     print(f"[START] {sid} | target: {expected}")

# # ===============================
# # POSE DATA INFERENCE
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions or model is None:
#         return

#     session = sessions[sid]
#     buffer = session["buffer"]

#     landmarks = data.get("landmarks")

#     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
#         return

#     # ===============================
#     # BUFFERING SEQUENCE
#     # ===============================
#     buffer.append(landmarks)
#     if len(buffer) > SEQ_LEN:
#         buffer.pop(0)

#     if len(buffer) < SEQ_LEN:
#         return

#     try:
#         input_tensor = np.array([buffer], dtype=np.float32)
#         prediction = model.predict(input_tensor, verbose=0)

#         max_idx = int(np.argmax(prediction[0]))
#         confidence = float(prediction[0][max_idx])

#         raw_label = labels[max_idx] if max_idx < len(labels) else "unknown"
#         clean_label = raw_label.replace("_", "").lower().strip()

#         # ===============================
#         # STABILISASI LABEL (MAJORITY VOTE)
#         # ===============================
#         session["prediction_history"].append(clean_label)
#         stable_label = Counter(session["prediction_history"]).most_common(1)[0][0]

#         # ===============================
#         # VALIDATION
#         # ===============================
#         expected = session["expected_label"]

#         is_match = (stable_label == expected)
#         is_valid = confidence >= VALID_THRESHOLD
#         is_correct = is_match and is_valid

#         # ===============================
#         # UPDATE STATS
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#         else:
#             session["stats"]["salah"] += 1

#         # ===============================
#         # RESPONSE KE CLIENT
#         # ===============================
#         emit("inference_result", {
#             "label": stable_label,
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "total_benar": session["stats"]["benar"],
#             "total_salah": session["stats"]["salah"]
#         })

#     except Exception as e:
#         print("[ERROR] Inference error:", e)

# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid

#     if sid not in sessions:
#         return

#     stats = sessions[sid]["stats"]
#     total = stats["benar"] + stats["salah"]

#     accuracy = stats["benar"] / total if total > 0 else 0

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": accuracy
#     })

#     print(f"[SUMMARY] {sid} | accuracy={accuracy:.2f}")


# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# from collections import deque, Counter

# # ===============================
# # CONFIG
# # ===============================
# MODEL_PATH = "pose_model_lstm.h5"
# LABELS_PATH = "labels_model.txt"

# SEQ_LEN = 20
# FEATURE_COUNT = 133

# VALID_THRESHOLD = 0.7
# STABILITY_WINDOW = 5

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []
# sessions = {}

# # ===============================
# # FIX LSTM COMPATIBILITY
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         kwargs.pop("time_major", None)
#         super().__init__(*args, **kwargs)

# # ===============================
# # LOAD MODEL
# # ===============================
# def load_pose_model():
#     global model, labels

#     try:
#         print(f"🔧 Loading model: {MODEL_PATH}")

#         model = tf.keras.models.load_model(
#             MODEL_PATH,
#             compile=False,
#             custom_objects={"LSTM": CustomLSTM}
#         )

#         print("✅ Model loaded")

#         if os.path.exists(LABELS_PATH):
#             with open(LABELS_PATH, "r") as f:
#                 labels = [line.strip() for line in f.readlines() if line.strip()]

#             print(f"✅ Labels loaded: {len(labels)} classes")
#             print("📌 Labels sample:", labels[:5])

#     except Exception as e:
#         print("❌ Model load error:", e)

# load_pose_model()

# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "prediction_history": deque(maxlen=STABILITY_WINDOW),
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": None
#     }

#     print(f"[CONNECT] {sid}")
#     emit("server_status", {"status": "ready"})

# # ===============================
# # DISCONNECT
# # ===============================
# @socketio.on("disconnect")
# def handle_disconnect():
#     sid = request.sid
#     sessions.pop(sid, None)
#     print(f"[DISCONNECT] {sid}")

# # ===============================
# # START SESSION
# # ===============================
# @socketio.on("start_session")
# def handle_start_session(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     expected = data.get("expected_label", "")

#     sessions[sid].update({
#         "buffer": [],
#         "prediction_history": deque(maxlen=STABILITY_WINDOW),
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": expected.lower().replace("_", " ").strip()
#     })

#     print(f"[START] {sid} | target: {expected}")

# # ===============================
# # POSE DATA INFERENCE
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions or model is None:
#         return

#     session = sessions[sid]
#     buffer = session["buffer"]

#     landmarks = data.get("landmarks")

#     if not isinstance(landmarks, list) or len(landmarks) != FEATURE_COUNT:
#         return

#     # ===============================
#     # BUFFERING SEQUENCE
#     # ===============================
#     buffer.append(landmarks)
#     if len(buffer) > SEQ_LEN:
#         buffer.pop(0)

#     if len(buffer) < SEQ_LEN:
#         return

#     try:
#         input_tensor = np.array([buffer], dtype=np.float32)
#         prediction = model.predict(input_tensor, verbose=0)

#         max_idx = int(np.argmax(prediction[0]))
#         confidence = float(prediction[0][max_idx])

#         # ===============================
#         # SAFE LABEL MAPPING
#         # ===============================
#         if len(labels) == 0:
#             raw_label = "unknown"
#         elif max_idx >= len(labels):
#             raw_label = "unknown"
#         else:
#             raw_label = labels[max_idx]

#         # ===============================
#         # NORMALISASI LABEL (FIX UTAMA)
#         # ===============================
#         clean_label = raw_label.replace("_", " ").lower().strip()

#         # ===============================
#         # STABILISASI LABEL
#         # ===============================
#         session["prediction_history"].append(clean_label)
#         stable_label = Counter(session["prediction_history"]).most_common(1)[0][0]

#         # ===============================
#         # NORMALISASI EXPECTED
#         # ===============================
#         expected = session["expected_label"]
#         expected = expected.replace("_", " ").lower().strip()

#         # ===============================
#         # VALIDATION
#         # ===============================
#         is_match = (stable_label == expected)
#         is_valid = confidence >= VALID_THRESHOLD
#         is_correct = is_match and is_valid

#         # ===============================
#         # UPDATE STATS
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#         else:
#             session["stats"]["salah"] += 1

#         # ===============================
#         # DEBUG (SANGAT DISARANKAN)
#         # ===============================
#         print(f"PRED: {stable_label} | EXPECTED: {expected} | CONF: {confidence:.2f}")

#         # ===============================
#         # RESPONSE KE CLIENT
#         # ===============================
#         emit("inference_result", {
#             "label": stable_label,
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "total_benar": session["stats"]["benar"],
#             "total_salah": session["stats"]["salah"]
#         })

#     except Exception as e:
#         print("[ERROR] Inference error:", e)

# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid

#     if sid not in sessions:
#         return

#     stats = sessions[sid]["stats"]
#     total = stats["benar"] + stats["salah"]

#     accuracy = stats["benar"] / total if total > 0 else 0

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": accuracy
#     })

#     print(f"[SUMMARY] {sid} | accuracy={accuracy:.2f}")

from flask import request
from flask_socketio import emit
from extensions import socketio
import numpy as np
import tensorflow as tf
import os
from collections import deque, Counter
import math
MAX_BUFFER_SIZE = 60
# ===============================
# CONFIG
# ===============================
MODEL_PATH = "pose_model_lstm.h5"
LABELS_PATH = "labels_lstm2.txt"

SEQ_LEN = 20
FEATURE_COUNT = 132

VALID_THRESHOLD = 0.7
STABILITY_WINDOW = 5

# ===============================
# GLOBAL STATE
# ===============================
model = None
labels = []
sessions = {}

# ===============================
# FIX LSTM COMPATIBILITY
# ===============================
class CustomLSTM(tf.keras.layers.LSTM):
    def __init__(self, *args, **kwargs):
        kwargs.pop("time_major", None)
        super().__init__(*args, **kwargs)

# ===============================
# LOAD MODEL + LABELS
# ===============================
def load_pose_model():
    global model, labels

    try:
        print(f"🔧 Loading model: {MODEL_PATH}")

        model = tf.keras.models.load_model(
            MODEL_PATH,
            compile=False,
            custom_objects={"LSTM": CustomLSTM}
        )

        print("✅ Model loaded")

        # ===============================
        # LOAD LABELS (STRICT)
        # ===============================
        if not os.path.exists(LABELS_PATH):
            raise FileNotFoundError(f"Labels file not found: {LABELS_PATH}")

        with open(LABELS_PATH, "r", encoding="utf-8") as f:
            labels = [l.strip().lower().replace("_", " ") for l in f if l.strip()]

        if len(labels) == 0:
            raise ValueError("Labels file is empty!")

        print(f"✅ Labels loaded: {len(labels)} classes")
        print("📌 Sample labels:", labels[:5])

    except Exception as e:
        print("❌ FATAL LOAD ERROR:", e)
        labels = []

load_pose_model()

# ===============================
# CONNECT
# ===============================
@socketio.on("connect")
def handle_connect():
    sid = request.sid

    sessions[sid] = {
        "buffer": [],
        "prediction_history": deque(maxlen=STABILITY_WINDOW),
        "stats": {"benar": 0, "salah": 0},
        "expected_label": None
    }

    print(f"[CONNECT] {sid}")
    emit("server_status", {"status": "ready"})

# ===============================
# DISCONNECT
# ===============================
@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    sessions.pop(sid, None)
    print(f"[DISCONNECT] {sid}")

# ===============================
# START SESSION
# ===============================
@socketio.on("start_session")
def handle_start_session(data):
    sid = request.sid

    if sid not in sessions:
        sessions[sid] = {
            "buffer": [],
            "prediction_history": deque(maxlen=STABILITY_WINDOW),
            "stats": {"benar": 0, "salah": 0},
            "expected_label": ""
        }

    data = data or {}

    expected = data.get("expected_label")
    if expected is None:
        expected = data.get("label")
    if expected is None:
        expected = data.get("nama_latihan")
    if expected is None:
        expected = ""

    normalized_expected = str(expected).lower().replace("_", " ").strip()

    sessions[sid].update({
        "buffer": [],
        "prediction_history": deque(maxlen=STABILITY_WINDOW),
        "stats": {"benar": 0, "salah": 0},
        "expected_label": normalized_expected
    })

    print(f"[START] {sid} | target: {normalized_expected}")

# ===============================
# INFERENCE
# ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions or model is None:
#         return

#     if len(labels) == 0:
#         print("❌ LABELS EMPTY → inference skipped")
#         return

#     session = sessions[sid]
#     buffer = session["buffer"]

#     landmarks = data.get("landmarks")

#     # Validasi landmarks list
#     if not isinstance(landmarks, list):
#         print(f"⚠️ [WARNING] landmarks bukan bertipe list untuk sid: {sid}")
#         return

#     # Validasi panjang landmarks (harus 133)
#     if len(landmarks) != FEATURE_COUNT:
#         print(f"⚠️ [WARNING] landmarks length is {len(landmarks)}, expected {FEATURE_COUNT}! Inference skipped.")
#         return

#     # ===============================
#     # BUFFER
#     # ===============================
#     buffer.append(landmarks)
#     if len(buffer) > SEQ_LEN:
#         buffer.pop(0)

#     if len(buffer) < SEQ_LEN:
#         return

#     try:
#         input_tensor = np.array([buffer], dtype=np.float32)
#         prediction = model.predict(input_tensor, verbose=0)

#         max_idx = int(np.argmax(prediction[0]))
#         confidence = float(prediction[0][max_idx])

#         # ===============================
#         # LABEL SAFETY & NORMALISASI
#         # ===============================
#         raw_label = labels[max_idx] if max_idx < len(labels) else "unknown"
#         clean_label = raw_label.lower().replace("_", " ").strip()

#         # ===============================
#         # STABILIZATION
#         # ===============================
#         session["prediction_history"].append(clean_label)
#         stable_label = Counter(session["prediction_history"]).most_common(1)[0][0]

#         # ===============================
#         # EXPECTED NORMALIZATION
#         # ===============================
#         expected = session.get("expected_label") or ""
#         expected = str(expected).replace("_", " ").lower().strip()

#         # ===============================
#         # MATCH LOGIC (STRICT)
#         # ===============================
#         is_match = (stable_label == expected)
#         is_valid = confidence >= VALID_THRESHOLD

#         # BONUS: noise guard
#         is_correct = is_match and is_valid

#         # ===============================
#         # STATS
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#         else:
#             session["stats"]["salah"] += 1

#         # ===============================
#         # DEBUG (IMPORTANT)
#         # ===============================
#         print(
#             f"ℹ️ [INFERENCE] sid: {sid} | "
#             f"landmarks length: {len(landmarks)} | "
#             f"tensor shape: {input_tensor.shape} | "
#             f"stable: {stable_label} | "
#             f"expected: {expected} | "
#             f"conf: {confidence:.2f} | "
#             f"match: {is_match}"
#         )

#         # ===============================
#         # EMIT
#         # ===============================
#         emit("inference_result", {
#             "label": stable_label,
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "total_benar": session["stats"]["benar"],
#             "total_salah": session["stats"]["salah"]
#         })

#     except Exception as e:
#         print("[ERROR] inference error:", e)

@socketio.on("send_pose_data")
def handle_pose_data(data):
    sid = request.sid

    if sid not in sessions or model is None:
        return

    if len(labels) == 0:
        print("❌ LABELS EMPTY → inference skipped")
        return

    session = sessions[sid]
    buffer = session["buffer"]

    landmarks = data.get("landmarks")

    # Validasi landmarks list
    if not isinstance(landmarks, list):
        print(f"⚠️ [WARNING] landmarks bukan bertipe list untuk sid: {sid}")
        return

    # Validasi panjang landmarks (harus 132/133 sesuai model)
    if len(landmarks) != FEATURE_COUNT:
        print(f"⚠️ [WARNING] landmarks length is {len(landmarks)}, expected {FEATURE_COUNT}! Inference skipped.")
        return

    # ===============================
    # BUFFER & RESAMPLING (YANG DIUBAH)
    # ===============================
    MAX_BUFFER_SIZE = 60 # Set maksimal riwayat frame yang disimpan (misal 2-3 detik)
    
    buffer.append(landmarks)
    
    # 1. Biarkan buffer menumpuk sampai MAX_BUFFER_SIZE (bukan langsung dipotong di SEQ_LEN)
    if len(buffer) > MAX_BUFFER_SIZE:
        buffer.pop(0)

    # 2. Tunggu sampai minimal ada SEQ_LEN (30) frame sebelum mulai memprediksi
    if len(buffer) < SEQ_LEN:
        return

    try:
        # 3. Ambil persis SEQ_LEN (30) frame secara merata dari total isi buffer saat ini
        indices = np.linspace(0, len(buffer) - 1, SEQ_LEN).astype(int)
        sampled_buffer = [buffer[i] for i in indices]

        # 4. Masukkan buffer yang sudah di-resample ke model
        input_tensor = np.array([sampled_buffer], dtype=np.float32)
        prediction = model.predict(input_tensor, verbose=0)

        max_idx = int(np.argmax(prediction[0]))
        confidence = float(prediction[0][max_idx])

        # ===============================
        # LABEL SAFETY & NORMALISASI
        # ===============================
        raw_label = labels[max_idx] if max_idx < len(labels) else "unknown"
        clean_label = raw_label.lower().replace("_", " ").strip()

        # ===============================
        # STABILIZATION
        # ===============================
        session["prediction_history"].append(clean_label)
        stable_label = Counter(session["prediction_history"]).most_common(1)[0][0]

        # ===============================
        # EXPECTED NORMALIZATION
        # ===============================
        expected = session.get("expected_label") or ""
        expected = str(expected).replace("_", " ").lower().strip()

        # ===============================
        # MATCH LOGIC (STRICT)
        # ===============================
        is_match = (stable_label == expected)
        is_valid = confidence >= VALID_THRESHOLD

        # BONUS: noise guard
        is_correct = is_match and is_valid

        # ===============================
        # STATS
        # ===============================
        if is_correct:
            session["stats"]["benar"] += 1
        else:
            session["stats"]["salah"] += 1

        # ===============================
        # DEBUG (IMPORTANT)
        # ===============================
        print(
            f"ℹ️ [INFERENCE] sid: {sid} | "
            f"buffer size: {len(buffer)} (sampled to {SEQ_LEN}) | "
            f"stable: {stable_label} | "
            f"expected: {expected} | "
            f"conf: {confidence:.2f} | "
            f"match: {is_match}"
        )

        # ===============================
        # EMIT
        # ===============================
        emit("inference_result", {
            "label": stable_label,
            "confidence": confidence,
            "is_valid": is_valid,
            "is_match": is_match,
            "is_correct": is_correct,
            "total_benar": session["stats"]["benar"],
            "total_salah": session["stats"]["salah"]
        })

    except Exception as e:
        print("[ERROR] inference error:", e)

# ===============================
# END EXERCISE
# ===============================
@socketio.on("end_exercise")
def handle_end_exercise():
    sid = request.sid

    if sid not in sessions:
        return

    stats = sessions[sid]["stats"]
    total = stats["benar"] + stats["salah"]

    accuracy = stats["benar"] / total if total > 0 else 0

    emit("exercise_summary", {
        "total_benar": stats["benar"],
        "total_salah": stats["salah"],
        "akurasi": accuracy
    })

    print(f"[SUMMARY] {sid} | accuracy={accuracy:.2f}")