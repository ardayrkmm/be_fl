# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time

# # ===============================
# # CONFIG
# # ===============================
# MODEL_PATH = "./lstm/coba_senin_15/pose_model_lstm.h5"
# LABELS_PATH = "./lstm/coba_senin_15/labels_lstm_baru.txt"
# MODEL_PATH_SPE = "./lstm/coba_senin_15/pose_model_spe.h5"
# LABELS_PATH_SPE = "./lstm/coba_senin_15/labels_lstm_spe.txt"



# SEQ_LEN = 20
# FEATURE_COUNT = 132
# VALID_THRESHOLD = 0.7

# SPECIALIST_THRESHOLDS = {
#     "calf raises": 0.35,
#     "straight leg raise": 0.50,
# }

# SMOOTHING_WINDOW = 5


# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []
# specialist_model = None
# specialist_labels = []

# sessions = {}

# SPECIALIST_TARGETS = {
#     "calf raises",
#     "straight leg raise",
# }


# # ===============================
# # FIX LSTM COMPATIBILITY
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         kwargs.pop("time_major", None)
#         super().__init__(*args, **kwargs)

# # ===============================
# # LOAD MODEL + LABELS
# # ===============================

# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False,
#         custom_objects={"LSTM": CustomLSTM}
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded")
#     print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
#     print(f"📌 {model_name} sample labels:", loaded_labels[:5])

#     return loaded_model, loaded_labels


# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )
# def get_label_index(label_list, target_label):
#     target = normalize_label(target_label)

#     for index, label in enumerate(label_list):
#         if normalize_label(label) == target:
#             return index

#     return None

# def load_pose_model():
#     global model, labels, specialist_model, specialist_labels

#     try:
#         model, labels = load_model_and_labels(
#             MODEL_PATH,
#             LABELS_PATH,
#             "MAIN MODEL"
#         )
#     except Exception as e:
#         print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
#         model = None
#         labels = []

#     try:
#         specialist_model, specialist_labels = load_model_and_labels(
#             MODEL_PATH_SPE,
#             LABELS_PATH_SPE,
#             "SPECIALIST MODEL"
#         )
#     except Exception as e:
#         print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
#         specialist_model = None
#         specialist_labels = []


# def select_model(expected_label):
#     expected = normalize_label(expected_label)

#     if (
#         expected in SPECIALIST_TARGETS
#         and specialist_model is not None
#         and len(specialist_labels) > 0
#     ):
#         threshold = SPECIALIST_THRESHOLDS.get(expected, 0.50)
#         return specialist_model, specialist_labels, threshold, "specialist"

#     return model, labels, VALID_THRESHOLD, "main"

# load_pose_model()

# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#     "buffer": [],
#     "stats": {
#         "benar": 0,
#         "salah": 0
#     },
#     "expected_label": "",
#     "start_time": None,
#     "specialist_scores": [],
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
#         sessions[sid] = {
#             "buffer": [],
#             "stats": {
#                 "benar": 0,
#                 "salah": 0
#             },
#             "expected_label": "",
#             "start_time": None
#         }

#     data = data or {}

#     expected = data.get("expectedLabel")
#     if expected is None:
#         expected = data.get("expected_label")
#     if expected is None:
#         expected = data.get("label")
#     if expected is None:
#         expected = data.get("nama_latihan")
#     if expected is None:
#         expected = ""

#     normalized_expected = normalize_label(expected)

#     sessions[sid].update({
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": normalized_expected,
#         "start_time": time.time()
#     })

#     print(f"[START] {sid} | target: {normalized_expected}")

#     emit("session_started", {
#         "expected_label": normalized_expected
#     })

# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     buffer = session["buffer"]

#     landmarks = data.get("landmarks")

#     if not isinstance(landmarks, list):
#         print(f"⚠️ landmarks bukan list | sid={sid}")
#         return

#     if len(landmarks) != FEATURE_COUNT:
#         print(
#             f"⚠️ landmarks length salah: {len(landmarks)}, "
#             f"expected {FEATURE_COUNT}"
#         )
#         return

#     buffer.append(landmarks)

#     if len(buffer) > SEQ_LEN:
#         buffer.pop(0)

#     if len(buffer) < SEQ_LEN:
#         return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([buffer], dtype=np.float32)
#         prediction = selected_model.predict(input_tensor, verbose=0)[0]

#         # ===============================
#         # SPECIALIST MODEL: CALF / STRAIGHT
#         # ===============================
#         if model_name == "specialist":
#             max_idx = int(np.argmax(prediction))
#             top_label = normalize_label(selected_labels[max_idx])
#             top_confidence = float(prediction[max_idx])

#             expected_idx = get_label_index(selected_labels, expected_norm)

#             if expected_idx is None:
#                 print(
#                     f"❌ Expected label tidak ada di specialist labels | "
#                     f"expected={expected_norm} | labels={selected_labels}"
#                 )
#                 return

#             expected_score = float(prediction[expected_idx])

#             scores = session.setdefault("specialist_scores", [])
#             scores.append(expected_score)

#             if len(scores) > SMOOTHING_WINDOW:
#                 scores.pop(0)

#             smoothed_score = sum(scores) / len(scores)

#             threshold = SPECIALIST_THRESHOLDS.get(expected_norm, 0.50)
#             is_correct = smoothed_score >= threshold

#             print(
#                 f"🎯 SPECIALIST | expected={expected_norm} | "
#                 f"expected_score={expected_score:.4f} | "
#                 f"smooth={smoothed_score:.4f} | "
#                 f"threshold={threshold:.2f} | "
#                 f"top={top_label}:{top_confidence:.4f} | "
#                 f"correct={is_correct}"
#             )

#             emit("inference_result", {
#                 "label": expected_norm if is_correct else "belum sesuai",
#                 "predicted_label": top_label,
#                 "confidence": smoothed_score,
#                 "top_confidence": top_confidence,
#                 "is_valid": is_correct,
#                 "is_match": is_correct,
#                 "is_correct": is_correct,
#                 "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#                 "model_used": model_name,
#                 "total_benar": session["stats"]["benar"],
#                 "total_salah": session["stats"]["salah"],
#             })
#             return

#         # ===============================
#         # MAIN MODEL
#         # ===============================
#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         print(
#             f"🧠 MAIN | pred={predicted_label} | "
#             f"expected={expected_norm} | "
#             f"conf={confidence:.2f} | "
#             f"match={is_match}"
#         )

#         emit("inference_result", {
#             "label": predicted_label,
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#             "model_used": model_name,
#             "total_benar": session["stats"]["benar"],
#             "total_salah": session["stats"]["salah"],
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)
# # 
# #  ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     stats = session["stats"]

#     total = stats["benar"] + stats["salah"]
#     akurasi = stats["benar"] / total if total > 0 else 0.0

#     durasi_latihan = 0.0
#     if session.get("start_time") is not None:
#         durasi_latihan = time.time() - session["start_time"]

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(
#         f"📊 [SUMMARY] sid={sid} | "
#         f"benar={stats['benar']} | "
#         f"salah={stats['salah']} | "
#         f"akurasi={akurasi:.2f} | "
#         f"durasi={durasi_latihan:.2f}s"
#     )

#     session.update({
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "start_time": None
#     })


# ===============================
# SEND POSE DATA - 1 MODEL SAJA
# ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     buffer = session["buffer"]

#     landmarks = data.get("landmarks")

#     if not isinstance(landmarks, list):
#         print(f"⚠️ landmarks bukan list | sid={sid}")
#         return

#     if len(landmarks) != FEATURE_COUNT:
#         print(
#             f"⚠️ landmarks length salah: {len(landmarks)}, "
#             f"expected {FEATURE_COUNT}"
#         )
#         return

#     buffer.append(landmarks)

#     if len(buffer) > SEQ_LEN:
#         buffer.pop(0)

#     if len(buffer) < SEQ_LEN:
#         return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([buffer], dtype=np.float32)
#         prediction = selected_model.predict(input_tensor, verbose=0)[0]

#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         print(
#             f"🧠 PREDICT | model={model_name} | "
#             f"shape={input_tensor.shape} | "
#             f"pred={predicted_label} | "
#             f"expected={expected_norm} | "
#             f"conf={confidence:.2f} | "
#             f"match={is_match}"
#         )

#         emit("inference_result", {
            
#             "label": predicted_label if is_correct else "Gerakan salah", 
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Perbaiki Posisi",
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time

# # ===============================
# # CONFIG - 1 MODEL SAJA
# # ===============================
# MODEL_PATH = "./lstm/coba_rabu_23/pose_model_lstm1.h5"
# LABELS_PATH = "./lstm/coba_rabu_23/labels_lstm_lutut1.txt"
# # MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# # LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"

# SEQ_LEN = 20
# FEATURE_COUNT = 132
# VALID_THRESHOLD = 0.7

# # MODEL_PATH = "./lstm/pose_model_lstm.h5"
# # LABELS_PATH = "./lstm/labels_lstm.txt"

# MODEL_PATH_SPE = "./lstm/coba_selasa_16/pose_model_lstm.h5"
# LABELS_PATH_SPE = "./lstm/coba_selasa_16/labels_lstm.txt"
# # MODEL_PATH_SPE_2 = "./lstm/coba_minggu_28/pose_model_spesial_2.h5"
# # LABELS_PATH_SPE_2 = "./lstm/coba_selasa_16/labels_lstm_spesial_2.txt"

# # SEQ_LEN = 30
# # FEATURE_COUNT = 132
# # VALID_THRESHOLD = 0.7
# # SPECIALIST_THRESHOLD = 0.7

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []

# specialist_model = None
# specialist_labels = []

# sessions = {}

# SPECIALIST_TARGETS = {
#     # "ankle alphabet exercise",
#     # "calf raises",
#     # "towel toe curl",
# }

# # ===============================
# # FIX LSTM COMPATIBILITY
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         kwargs.pop("time_major", None)
#         super().__init__(*args, **kwargs)


# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )


# # ===============================
# # LOAD MODEL + LABELS
# # ===============================
# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False,
#         custom_objects={"LSTM": CustomLSTM}
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded")
#     print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
#     print(f"📌 {model_name} labels:", loaded_labels)
#     print(f"📌 {model_name} input shape:", loaded_model.input_shape)
#     print(f"📌 {model_name} output shape:", loaded_model.output_shape)

#     return loaded_model, loaded_labels


# def load_pose_model():
#     global model, labels, specialist_model, specialist_labels

#     try:
#         model, labels = load_model_and_labels(
#             MODEL_PATH,
#             LABELS_PATH,
#             "MAIN MODEL"
#         )
#     except Exception as e:
#         print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
#         model = None
#         labels = []

#     try:
#         specialist_model, specialist_labels = load_model_and_labels(
#             MODEL_PATH_SPE,
#             LABELS_PATH_SPE,
#             "SPECIALIST MODEL"
#         )
#     except Exception as e:
#         print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
#         specialist_model = None
#         specialist_labels = []

# def select_model(expected_label):
#     expected = normalize_label(expected_label)

#     if (
#         expected in SPECIALIST_TARGETS
#         and specialist_model is not None
#         and len(specialist_labels) > 0
#     ):
#         return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"

#     return model, labels, VALID_THRESHOLD, "main"

# load_pose_model()


# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": "",
#         "start_time": None
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
#         sessions[sid] = {
#             "buffer": [],
#             "stats": {
#                 "benar": 0,
#                 "salah": 0
#             },
#             "expected_label": "",
#             "start_time": None
#         }

#     data = data or {}

#     expected = data.get("expectedLabel")
#     if expected is None:
#         expected = data.get("expected_label")
#     if expected is None:
#         expected = data.get("label")
#     if expected is None:
#         expected = data.get("nama_latihan")
#     if expected is None:
#         expected = ""

#     normalized_expected = normalize_label(expected)

#     sessions[sid].update({
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": normalized_expected,
#         "start_time": time.time()
#     })

#     print(f"[START] {sid} | target: {normalized_expected}")

#     emit("session_started", {
#         "expected_label": normalized_expected
#     })



# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]

#     # 1. Terima paket 30 frame langsung dari Flutter
#     sequence_buffer = data.get("landmarks")

#     # Validasi Dasar
#     if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0:
#         return

#     # 2. Cek apakah benar ini 2D Array (List of List)
#     if not isinstance(sequence_buffer[0], list):
#         print(f"⚠️ Salah format! Flutter harus kirim List<List<double>> | sid={sid}")
#         return

#     # 3. Cek apakah jumlah frame-nya pas 30 (SEQ_LEN)
#     if len(sequence_buffer) != SEQ_LEN:
#         return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         # 4. SULAP LANGSUNG JADI TENSOR (Tidak perlu pakai buffer Python lagi!)
#         input_tensor = np.array([sequence_buffer], dtype=np.float32)
#         prediction = selected_model.predict(input_tensor, verbose=0)[0]

#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         print(
#             f"🧠 PREDICT BATCH | model={model_name} | "
#             f"shape={input_tensor.shape} | "
#             f"pred={predicted_label} | "
#             f"expected={expected_norm} | "
#             f"conf={confidence:.2f} | "
#             f"match={is_match}"
#         )

#         emit("inference_result", {
#             "label": predicted_label if is_correct else "Gerakan salah", 
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     stats = session["stats"]

#     total = stats["benar"] + stats["salah"]
#     akurasi = (
#     (stats["benar"] / total) * 100
#     if total > 0
#     else 0.0
# )

#     durasi_latihan = 0.0
#     if session.get("start_time") is not None:
#         durasi_latihan = time.time() - session["start_time"]

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(
#         f"📊 [SUMMARY] sid={sid} | "
#         f"benar={stats['benar']} | "
#         f"salah={stats['salah']} | "
#         f"akurasi={akurasi:.2f} | "
#         f"durasi={durasi_latihan:.2f}s"
#     )

#     session.update({
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": "",
#         "start_time": None
#     })

# ===============================
# CONFIG
# ===============================
# MODEL_PATH = "./lstm/coba_rabu_23/pose_model_lstm1.h5"
# LABELS_PATH = "./lstm/coba_rabu_23/labels_lstm_lutut1.txt"

# MODEL_PATH = "./lstm/coba_senin_15/pose_model_lstm.h5"
# LABELS_PATH = "./lstm/coba_senin_15/labels_lstm_baru.txt"

# MODEL_PATH = "./lstm/coba_rabu_23/pose_model_lstm1.h5"
# LABELS_PATH = "./lstm/coba_rabu_23/labels_lstm_lutut1.txt"
# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time


# MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"
# # MODEL_PATH = "./lstm/pose_model_lstm.h5"
# # LABELS_PATH = "./lstm/labels_lstm.txt"
# SEQ_LEN = 20
# FEATURE_COUNT = 132
# VALID_THRESHOLD = 0.7
# SPECIALIST_THRESHOLD = 0.7  # Diaktifkan untuk model spesialis

# MODEL_PATH_SPE = "./lstm/coba_rabu_23/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_SPE = "./lstm/coba_rabu_23/labels_lstm_spesial_2.txt"

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []

# specialist_model = None
# specialist_labels = []

# sessions = {}

# SPECIALIST_TARGETS = {
#     # "ankle alphabet exercise",
#     # "calf raises",
#     # "towel toe curl",
# }

# # ===============================
# # FIX LSTM COMPATIBILITY
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         kwargs.pop("time_major", None)
#         super().__init__(*args, **kwargs)


# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )


# # ===============================
# # LOAD MODEL + LABELS
# # ===============================
# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False,
#         custom_objects={"LSTM": CustomLSTM}
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded")
#     print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
#     print(f"📌 {model_name} labels:", loaded_labels)
#     print(f"📌 {model_name} input shape:", loaded_model.input_shape)
#     print(f"📌 {model_name} output shape:", loaded_model.output_shape)

#     return loaded_model, loaded_labels


# def load_pose_model():
#     global model, labels, specialist_model, specialist_labels

#     try:
#         model, labels = load_model_and_labels(
#             MODEL_PATH,
#             LABELS_PATH,
#             "MAIN MODEL"
#         )
#     except Exception as e:
#         print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
#         model = None
#         labels = []

#     try:
#         specialist_model, specialist_labels = load_model_and_labels(
#             MODEL_PATH_SPE,
#             LABELS_PATH_SPE,
#             "SPECIALIST MODEL"
#         )
#     except Exception as e:
#         print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
#         specialist_model = None
#         specialist_labels = []

# def select_model(expected_label, force_specialist=False):
#     expected = normalize_label(expected_label)

#     # Pakai model spesialis jika masuk SPECIALIST_TARGETS atau dipaksa (force_specialist=True)
#     if (
#         (expected in SPECIALIST_TARGETS or force_specialist)
#         and specialist_model is not None
#         and len(specialist_labels) > 0
#     ):
#         return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"

#     return model, labels, VALID_THRESHOLD, "main"

# load_pose_model()


# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "force_specialist": False
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
#     data = data or {}

#     expected = data.get("expectedLabel")
#     if expected is None:
#         expected = data.get("expected_label")
#     if expected is None:
#         expected = data.get("label")
#     if expected is None:
#         expected = data.get("nama_latihan")
#     if expected is None:
#         expected = ""

#     normalized_expected = normalize_label(expected)

#     # Re-inisialisasi session setiap kali latihan baru dimulai
#     sessions[sid] = {
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": normalized_expected,
#         "start_time": time.time(),
#         "consecutive_errors": 0,
#         "force_specialist": False
#     }

#     print(f"[START] {sid} | target: {normalized_expected}")

#     emit("session_started", {
#         "expected_label": normalized_expected
#     })


# # ===============================
# # RECEIVE & PREDICT
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     sequence_buffer = data.get("landmarks")

#     # Validasi Dasar
#     if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0:
#         return

#     if not isinstance(sequence_buffer[0], list):
#         print(f"⚠️ Salah format! Flutter harus kirim List<List<double>> | sid={sid}")
#         return

#     if len(sequence_buffer) != SEQ_LEN:
#         return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)
    
#     # Cek apakah harus menggunakan model spesialis (karena salah beruntun)
#     force_specialist = session.get("force_specialist", False)

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm, force_specialist)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([sequence_buffer], dtype=np.float32)
#         if np.sum(np.abs(input_tensor)) < 1e-5:
#             print(f"👻 [OUT OF FRAME] {sid} hilang dari layar!")
#             emit("inference_result", {
#                 "label": "Tidak terdeteksi",
#                 "confidence": 0.0,
#                 "is_valid": False,
#                 "is_match": False,
#                 "is_correct": False,
#                 "feedback": "Pastikan seluruh tubuh masuk ke kamera!",
#                 "active_model": model_name
#             })
#             return  # Langsung berhenti, JANGAN lakukan prediksi model

#         # 2. Cek apakah user nge-freeze / diam mematung (Varians/pergerakan nyaris 0)
#         # Angka 1e-4 bisa disesuaikan kalau terlalu sensitif
#         if np.var(input_tensor) < 1e-4:
#             print(f"🗿 [STANDBY] {sid} diam tidak bergerak.")
#             emit("inference_result", {
#                 "label": "Standby",
#                 "confidence": 0.0,
#                 "is_valid": False,
#                 "is_match": False,
#                 "is_correct": False,
#                 "feedback": "Ayo mulai bergerak!",
#                 "active_model": model_name
#             })
#             return  # Langsung berhenti juga
#         prediction = selected_model.predict(input_tensor, verbose=0)[0]

#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         # ===============================
#         # UPDATE STATS & PENGKONDISIAN MODEL
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#             session["consecutive_errors"] = 0  # Reset counter jika benar
#         else:
#             session["stats"]["salah"] += 1
#             session["consecutive_errors"] += 1 # Tambah counter jika salah

#             # Ganti model jika salah 3x beruntun
#             if session["consecutive_errors"] >= 3 and not session["force_specialist"]:
#                 print(f"⚠️ [WARNING] {sid} salah 3x beruntun! Pindah ke model {model_name} -> specialist.")
#                 session["force_specialist"] = True 

#         print(
#             f"🧠 PREDICT BATCH | model={model_name} | "
#             f"shape={input_tensor.shape} | "
#             f"pred={predicted_label} | expected={expected_norm} | "
#             f"conf={confidence:.2f} | match={is_match} | "
#             f"Salah beruntun={session['consecutive_errors']}"
#         )

#         emit("inference_result", {
#             "label": predicted_label if is_correct else "Gerakan salah", 
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#             "active_model": model_name
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     stats = session["stats"]

#     total = stats["benar"] + stats["salah"]
#     akurasi = (
#         (stats["benar"] / total) * 100
#         if total > 0
#         else 0.0
#     )

#     durasi_latihan = 0.0
#     if session.get("start_time") is not None:
#         durasi_latihan = time.time() - session["start_time"]

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(
#         f"📊 [SUMMARY] sid={sid} | "
#         f"benar={stats['benar']} | "
#         f"salah={stats['salah']} | "
#         f"akurasi={akurasi:.2f} | "
#         f"durasi={durasi_latihan:.2f}s"
#     )

#     # Reset session untuk antisipasi jika user tidak disconnect tapi mengulang
#     session.update({
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "force_specialist": False
#     })

# MODEL_PATH = "./lstm/coba_rabu_23/pose_model_lstm1.h5"
# LABELS_PATH = "./lstm/coba_rabu_23/labels_lstm_lutut1.txt"
# # MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# # LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"
# MODEL_PATH = "./lstm/pose_model_lstm.h5"
# LABELS_PATH = "./lstm/labels_lstm.txt"

# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time


# MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"

# SEQ_LEN = 20
# FEATURE_COUNT = 132
# VALID_THRESHOLD = 0.7
# SPECIALIST_THRESHOLD = 0.7  # Diaktifkan untuk model spesialis

# MODEL_PATH_SPE = "./lstm/coba_rabu_23/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_SPE = "./lstm/coba_rabu_23/labels_lstm_spesial_2.txt"

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []

# specialist_model = None
# specialist_labels = []

# sessions = {}

# SPECIALIST_TARGETS = {
#     # "ankle alphabet exercise",
#     # "calf raises",
#     # "towel toe curl",
# }

# # ===============================
# # FIX LSTM COMPATIBILITY
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         kwargs.pop("time_major", None)
#         super().__init__(*args, **kwargs)


# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )


# # ===============================
# # LOAD MODEL + LABELS
# # ===============================
# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False,
#         custom_objects={"LSTM": CustomLSTM}
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded")
#     print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
#     print(f"📌 {model_name} labels:", loaded_labels)
#     print(f"📌 {model_name} input shape:", loaded_model.input_shape)
#     print(f"📌 {model_name} output shape:", loaded_model.output_shape)

#     return loaded_model, loaded_labels


# def load_pose_model():
#     global model, labels, specialist_model, specialist_labels

#     try:
#         model, labels = load_model_and_labels(
#             MODEL_PATH,
#             LABELS_PATH,
#             "MAIN MODEL"
#         )
#     except Exception as e:
#         print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
#         model = None
#         labels = []

#     try:
#         specialist_model, specialist_labels = load_model_and_labels(
#             MODEL_PATH_SPE,
#             LABELS_PATH_SPE,
#             "SPECIALIST MODEL"
#         )
#     except Exception as e:
#         print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
#         specialist_model = None
#         specialist_labels = []

# def select_model(expected_label, force_specialist=False):
#     expected = normalize_label(expected_label)

#     # Pakai model spesialis jika masuk SPECIALIST_TARGETS atau dipaksa (force_specialist=True)
#     if (
#         (expected in SPECIALIST_TARGETS or force_specialist)
#         and specialist_model is not None
#         and len(specialist_labels) > 0
#     ):
#         return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"

#     return model, labels, VALID_THRESHOLD, "main"

# load_pose_model()


# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "force_specialist": False
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
#     data = data or {}

#     expected = data.get("expectedLabel")
#     if expected is None:
#         expected = data.get("expected_label")
#     if expected is None:
#         expected = data.get("label")
#     if expected is None:
#         expected = data.get("nama_latihan")
#     if expected is None:
#         expected = ""

#     normalized_expected = normalize_label(expected)

#     # Re-inisialisasi session setiap kali latihan baru dimulai
#     sessions[sid] = {
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": normalized_expected,
#         "start_time": time.time(),
#         "consecutive_errors": 0,
#         "force_specialist": False
#     }

#     print(f"[START] {sid} | target: {normalized_expected}")

#     emit("session_started", {
#         "expected_label": normalized_expected
#     })


# # ===============================
# # RECEIVE & PREDICT
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     sequence_buffer = data.get("landmarks")

#     # Validasi Dasar
#     if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0:
#         return

#     if not isinstance(sequence_buffer[0], list):
#         print(f"⚠️ Salah format! Flutter harus kirim List<List<double>> | sid={sid}")
#         return

#     if len(sequence_buffer) != SEQ_LEN:
#         return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)
    
#     # Cek apakah harus menggunakan model spesialis (karena salah beruntun)
#     force_specialist = session.get("force_specialist", False)

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm, force_specialist)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([sequence_buffer], dtype=np.float32)
#         if np.sum(np.abs(input_tensor)) < 1e-5:
#             print(f"👻 [OUT OF FRAME] {sid} hilang dari layar!")
#             emit("inference_result", {
#                 "label": "Tidak terdeteksi",
#                 "confidence": 0.0,
#                 "is_valid": False,
#                 "is_match": False,
#                 "is_correct": False,
#                 "feedback": "Pastikan seluruh tubuh masuk ke kamera!",
#                 "active_model": model_name
#             })
#             return  # Langsung berhenti, JANGAN lakukan prediksi model

#         # 2. Cek apakah user nge-freeze / diam mematung (Varians/pergerakan nyaris 0)
#         # Angka 1e-4 bisa disesuaikan kalau terlalu sensitif
#         if np.var(input_tensor) < 1e-4:
#             print(f"🗿 [STANDBY] {sid} diam tidak bergerak.")
#             emit("inference_result", {
#                 "label": "Standby",
#                 "confidence": 0.0,
#                 "is_valid": False,
#                 "is_match": False,
#                 "is_correct": False,
#                 "feedback": "Ayo mulai bergerak!",
#                 "active_model": model_name
#             })
#             return  # Langsung berhenti juga
        
#         prediction = selected_model.predict(input_tensor, verbose=0)[0]

#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         # ===============================
#         # UPDATE STATS & PENGKONDISIAN MODEL
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#             session["consecutive_errors"] = 0  # Reset counter jika benar
#         else:
#             session["stats"]["salah"] += 1
#             session["consecutive_errors"] += 1 # Tambah counter jika salah

#             # Ganti model BOLAK-BALIK jika salah 3x beruntun
#             if session["consecutive_errors"] >= 3:
#                 # Toggle model: Kalau False jadi True, kalau True jadi False
#                 session["force_specialist"] = not session.get("force_specialist", False)
#                 # Reset error counter supaya model baru dikasih kesempatan 3x lagi sebelum ditukar balik
#                 session["consecutive_errors"] = 0 
                
#                 new_model_name = "specialist" if session["force_specialist"] else "main"
#                 print(f"⚠️ [WARNING] {sid} salah 3x beruntun! Pindah mode mencari ke -> {new_model_name}.")

#         print(
#             f"🧠 PREDICT BATCH | model={model_name} | "
#             f"shape={input_tensor.shape} | "
#             f"pred={predicted_label} | expected={expected_norm} | "
#             f"conf={confidence:.2f} | match={is_match} | "
#             f"Salah beruntun={session['consecutive_errors']}"
#         )

#         emit("inference_result", {
#             "label": predicted_label if is_correct else "Gerakan salah", 
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#             "active_model": model_name
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     stats = session["stats"]

#     total = stats["benar"] + stats["salah"]
#     akurasi = (
#         (stats["benar"] / total) * 100
#         if total > 0
#         else 0.0
#     )

#     durasi_latihan = 0.0
#     if session.get("start_time") is not None:
#         durasi_latihan = time.time() - session["start_time"]

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(
#         f"📊 [SUMMARY] sid={sid} | "
#         f"benar={stats['benar']} | "
#         f"salah={stats['salah']} | "
#         f"akurasi={akurasi:.2f} | "
#         f"durasi={durasi_latihan:.2f}s"
#     )

#     # Reset session untuk antisipasi jika user tidak disconnect tapi mengulang
#     session.update({
#         "buffer": [],
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "force_specialist": False
#     })

# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time

# # ===============================
# # CONFIG - 3 LEVEL MODEL
# # ===============================
# SEQ_LEN = 30
# FEATURE_COUNT = 132
# VALID_THRESHOLD = 0.7
# MAX_FAILURES = 3  # Jumlah salah berturut-turut sebelum turun level



# # SEQ_LEN = 20
# # FEATURE_COUNT = 132
# # VALID_THRESHOLD = 0.7

# # MODEL_PATH = "./lstm/pose_model_lstm.h5"
# # LABELS_PATH = "./lstm/labels_lstm.txt"

# # LEVEL 1 (Semua Gerakan)
# MODEL_PATH_L1 = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# LABELS_PATH_L1 = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"

# # LEVEL 2 (4 Gerakan Khusus)
# MODEL_PATH_L2 = "./lstm/coba_minggu_28/pose_model_lstm_spesial.h5"
# LABELS_PATH_L2 = "./lstm/coba_minggu_28/labels_lstm_spesial.txt"

# # LEVEL 3 (1 Gerakan Spesifik)
# MODEL_PATH_L3 = "./lstm/coba_minggu_28/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_L3 = "./lstm/coba_minggu_28/labels_lstm_spesial_2.txt"

# # Target gerakan untuk masing-masing level (sudah dinormalisasi huruf kecil & spasi)
# LEVEL_2_TARGETS = {
#     "knee to chest",
#     "towel toe curl",
#     "ankle alphabet exercise",
#     "calf raises"
# }

# LEVEL_3_TARGETS = {
#     "calf raises"
# }

# # ===============================
# # GLOBAL STATE
# # ===============================
# model_l1, labels_l1 = None, []
# model_l2, labels_l2 = None, []
# model_l3, labels_l3 = None, []
# sessions = {}

# # ===============================
# # FIX LSTM COMPATIBILITY
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         kwargs.pop("time_major", None)
#         super().__init__(*args, **kwargs)

# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )

# # ===============================
# # LOAD MODEL + LABELS
# # ===============================
# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False,
#         custom_objects={"LSTM": CustomLSTM}
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded | {len(loaded_labels)} classes")
#     return loaded_model, loaded_labels

# def load_all_models():
#     global model_l1, labels_l1, model_l2, labels_l2, model_l3, labels_l3

#     try:
#         model_l1, labels_l1 = load_model_and_labels(MODEL_PATH_L1, LABELS_PATH_L1, "LEVEL 1 MODEL")
#     except Exception as e:
#         print("❌ FATAL LEVEL 1 MODEL LOAD ERROR:", e)

#     try:
#         model_l2, labels_l2 = load_model_and_labels(MODEL_PATH_L2, LABELS_PATH_L2, "LEVEL 2 MODEL")
#     except Exception as e:
#         print("⚠️ LEVEL 2 MODEL LOAD ERROR:", e)

#     try:
#         model_l3, labels_l3 = load_model_and_labels(MODEL_PATH_L3, LABELS_PATH_L3, "LEVEL 3 MODEL")
#     except Exception as e:
#         print("⚠️ LEVEL 3 MODEL LOAD ERROR:", e)

# # Jalankan saat script diinisialisasi
# load_all_models()

# # ===============================
# # DYNAMIC MODEL SELECTION
# # ===============================
# def select_model(expected_norm, current_level):
#     # Cek apakah boleh dan bisa pakai Level 3
#     if current_level == 3 and expected_norm in LEVEL_3_TARGETS and model_l3 is not None:
#         return model_l3, labels_l3, "LEVEL 3"
    
#     # Cek apakah boleh dan bisa pakai Level 2
#     if current_level >= 2 and expected_norm in LEVEL_2_TARGETS and model_l2 is not None:
#         return model_l2, labels_l2, "LEVEL 2"
    
#     # Default pakai Level 1
#     return model_l1, labels_l1, "LEVEL 1"


# # ===============================
# # CONNECT / DISCONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid
#     print(f"[CONNECT] {sid}")
#     emit("server_status", {"status": "ready"})

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
#     data = data or {}

#     expected = data.get("expectedLabel") or data.get("expected_label") or data.get("label") or data.get("nama_latihan") or ""
#     normalized_expected = normalize_label(expected)

#     sessions[sid] = {
#         "stats": {
#             "benar": 0,
#             "salah": 0
#         },
#         "expected_label": normalized_expected,
#         "start_time": time.time(),
#         "consecutive_failures": 0,  # Melacak kegagalan beruntun
#         "current_level": 1          # Mulai selalu dari Level 1
#     }

#     print(f"[START] {sid} | target: {normalized_expected} | Mulai di LEVEL 1")
#     emit("session_started", {"expected_label": normalized_expected})


# # ===============================
# # INFERENCE LOGIC
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid
#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     sequence_buffer = data.get("landmarks")

#     # Validasi Dasar
#     if not isinstance(sequence_buffer, list) or len(sequence_buffer) != SEQ_LEN:
#         return
#     if not isinstance(sequence_buffer[0], list):
#         print(f"⚠️ Format Salah! Harusnya List<List<double>> | sid={sid}")
#         return

#     expected_norm = session.get("expected_label", "")
#     current_level = session.get("current_level", 1)

#     # Pilih model berdasarkan level dan ketersediaan target gerakan
#     selected_model, selected_labels, model_name = select_model(expected_norm, current_level)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([sequence_buffer], dtype=np.float32)
#         prediction = selected_model.predict(input_tensor, verbose=0)[0]

#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])
#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = (predicted_label == expected_norm)
#         is_valid = (confidence >= VALID_THRESHOLD)
#         is_correct = is_match and is_valid

#         # === UPDATE STATISTIK & LOGIKA DOWNGRADE ===
#         if is_correct:
#             session["stats"]["benar"] += 1
#             session["consecutive_failures"] = 0  # Reset kegagalan jika berhasil
#         else:
#             session["stats"]["salah"] += 1
#             session["consecutive_failures"] += 1
            
#             # Cek apakah butuh turun level
#             if session["consecutive_failures"] >= MAX_FAILURES:
#                 if session["current_level"] == 1 and expected_norm in LEVEL_2_TARGETS:
#                     session["current_level"] = 2
#                     session["consecutive_failures"] = 0
#                     print(f"📉 [DOWNGRADE] {sid} kesulitan. Turun ke LEVEL 2 untuk {expected_norm}")
#                     emit("level_changed", {"new_level": 2, "message": "Pindah ke model bantuan level 2"})
                
#                 elif session["current_level"] == 2 and expected_norm in LEVEL_3_TARGETS:
#                     session["current_level"] = 3
#                     session["consecutive_failures"] = 0
#                     print(f"📉 [DOWNGRADE] {sid} kesulitan. Turun ke LEVEL 3 untuk {expected_norm}")
#                     emit("level_changed", {"new_level": 3, "message": "Pindah ke model khusus 1 gerakan"})

#         print(
#             f"🧠 PREDICT | model={model_name} | "
#             f"pred={predicted_label} | "
#             f"expected={expected_norm} | "
#             f"conf={confidence:.2f} | "
#             f"benar={is_correct} | "
#             f"fails={session['consecutive_failures']}/3"
#         )

#         emit("inference_result", {
#             "label": predicted_label if is_correct else "Gerakan salah", 
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "current_level": session["current_level"],
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid
#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     stats = session["stats"]
#     total = stats["benar"] + stats["salah"]
    
#     akurasi = (stats["benar"] / total) * 100 if total > 0 else 0.0
#     durasi_latihan = time.time() - session["start_time"] if session.get("start_time") else 0.0

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(
#         f"📊 [SUMMARY] sid={sid} | "
#         f"benar={stats['benar']} | salah={stats['salah']} | "
#         f"akurasi={akurasi:.2f}% | durasi={durasi_latihan:.2f}s"
#     )
    
#     # Hapus data sesi lama agar mulai dari nol jika latihan lagi
#     sessions.pop(sid, None)    


# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time

# # --- 1. PATH MODEL MAIN ---
# MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"
# VALID_THRESHOLD = 0.7

# # --- 2. PATH MODEL SPECIALIST ---
# MODEL_PATH_SPE = "./lstm/coba_rabu_23/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_SPE = "./lstm/coba_rabu_23/labels_lstm_spesial_2.txt"
# SPECIALIST_THRESHOLD = 0.7 

# # --- 3. PATH MODEL BILSTM (Silakan Sesuaikan) ---
# MODEL_PATH_BILSTM = "./lstm/cobaLagi/pose_model_bilstm.h5"
# LABELS_PATH_BILSTM = "./lstm/cobaLagi/labels_lstm_lutut.txt"
# BILSTM_THRESHOLD = 0.7

# SEQ_LEN = 20
# FEATURE_COUNT = 132

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []

# specialist_model = None
# specialist_labels = []

# bilstm_model = None
# bilstm_labels = []

# sessions = {}

# SPECIALIST_TARGETS = {
#     # "ankle alphabet exercise",
#     # "calf raises",
#     # "towel toe curl",
# }

# # ===============================
# # FIX LSTM COMPATIBILITY
# # ===============================
# # ===============================
# class CustomLSTM(tf.keras.layers.LSTM):
#     def __init__(self, *args, **kwargs):
#         # 1. Hapus time_major saat inisialisasi layer
#         kwargs.pop("time_major", None)
#         super().__init__(*args, **kwargs)

#     @classmethod
#     def from_config(cls, config):
#         # 2. Hapus time_major dari dictionary konfigurasi bawaan .h5
#         config.pop("time_major", None)
#         # 3. Paksa Keras untuk langsung menggunakan class ini (bukan super class-nya)
#         return cls(**config)


# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )

# # ===============================
# # LOAD MODEL + LABELS
# # ===============================
# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False,
#         custom_objects={"LSTM": CustomLSTM}
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded")
#     print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
#     print(f"📌 {model_name} labels:", loaded_labels)
    
#     return loaded_model, loaded_labels


# def load_pose_model():
#     global model, labels, specialist_model, specialist_labels, bilstm_model, bilstm_labels

#     try:
#         model, labels = load_model_and_labels(MODEL_PATH, LABELS_PATH, "MAIN MODEL")
#     except Exception as e:
#         print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
#         model = None; labels = []

#     try:
#         specialist_model, specialist_labels = load_model_and_labels(MODEL_PATH_SPE, LABELS_PATH_SPE, "SPECIALIST MODEL")
#     except Exception as e:
#         print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
#         specialist_model = None; specialist_labels = []

#     try:
#         bilstm_model, bilstm_labels = load_model_and_labels(MODEL_PATH_BILSTM, LABELS_PATH_BILSTM, "BILSTM MODEL")
#     except Exception as e:
#         print("⚠️ BILSTM MODEL LOAD ERROR:", e)
#         bilstm_model = None; bilstm_labels = []

# # Update logika pemilihan model
# def select_model(expected_label, active_model_type="main"):
#     expected = normalize_label(expected_label)

#     # Tetap gunakan specialist jika masuk target khusus (opsional)
#     if expected in SPECIALIST_TARGETS and active_model_type == "main":
#         active_model_type = "specialist"

#     # Kembalikan model sesuai state yang diminta
#     if active_model_type == "specialist" and specialist_model is not None and len(specialist_labels) > 0:
#         return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"
    
#     elif active_model_type == "bilstm" and bilstm_model is not None and len(bilstm_labels) > 0:
#         return bilstm_model, bilstm_labels, BILSTM_THRESHOLD, "bilstm"
    
#     # Fallback selalu ke Main
#     return model, labels, VALID_THRESHOLD, "main"

# load_pose_model()


# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "active_model_type": "main" # <-- Diubah dari boolean ke string state
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
#     data = data or {}

#     expected = data.get("expectedLabel") or data.get("expected_label") or data.get("label") or data.get("nama_latihan") or ""
#     normalized_expected = normalize_label(expected)

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": normalized_expected,
#         "start_time": time.time(),
#         "consecutive_errors": 0,
#         "active_model_type": "main" # <-- Mulai selalu dari Main
#     }

#     print(f"[START] {sid} | target: {normalized_expected}")
#     emit("session_started", {"expected_label": normalized_expected})


# # ===============================
# # RECEIVE & PREDICT
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     sequence_buffer = data.get("landmarks")

#     if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0: return
#     if not isinstance(sequence_buffer[0], list): return
#     if len(sequence_buffer) != SEQ_LEN: return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)
    
#     # Ambil jenis model yang sedang aktif
#     active_model_type = session.get("active_model_type", "main")

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm, active_model_type)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([sequence_buffer], dtype=np.float32)
#         if np.sum(np.abs(input_tensor)) < 1e-5:
#             emit("inference_result", {
#                 "label": "Tidak terdeteksi",
#                 "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
#                 "feedback": "Pastikan seluruh tubuh masuk ke kamera!",
#                 "active_model": model_name
#             })
#             return 

#         if np.var(input_tensor) < 1e-4:
#             emit("inference_result", {
#                 "label": "Standby",
#                 "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
#                 "feedback": "Ayo mulai bergerak!",
#                 "active_model": model_name
#             })
#             return 
        
#         prediction = selected_model.predict(input_tensor, verbose=0)[0]
#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         # ===============================
#         # UPDATE STATS & ROTASI MODEL
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#             session["consecutive_errors"] = 0
#         else:
#             session["stats"]["salah"] += 1
#             session["consecutive_errors"] += 1

#             # Rotasi 3 model jika salah 3x beruntun
#             if session["consecutive_errors"] >= 3:
#                 current_type = session["active_model_type"]
                
#                 # Logika Rotasi
#                 if current_type == "main":
#                     next_type = "specialist"
#                 elif current_type == "specialist":
#                     next_type = "bilstm"
#                 else: # Jika current_type adalah "bilstm", kembalikan ke "main"
#                     next_type = "main"

#                 session["active_model_type"] = next_type
#                 session["consecutive_errors"] = 0 
                
#                 print(f"⚠️ [WARNING] {sid} salah 3x beruntun! Pindah mode dari {current_type} -> {next_type}.")

#         print(
#             f"🧠 PREDICT BATCH | model={model_name} | "
#             f"pred={predicted_label} | expected={expected_norm} | "
#             f"conf={confidence:.2f} | match={is_match} | "
#             f"Salah beruntun={session['consecutive_errors']}"
#         )

#         emit("inference_result", {
#             "label": predicted_label if is_correct else "Gerakan salah", 
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#             "active_model": model_name
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid
#     if sid not in sessions: return

#     session = sessions[sid]
#     stats = session["stats"]
#     total = stats["benar"] + stats["salah"]
#     akurasi = ((stats["benar"] / total) * 100) if total > 0 else 0.0
#     durasi_latihan = time.time() - session["start_time"] if session.get("start_time") else 0.0

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(f"📊 [SUMMARY] sid={sid} | benar={stats['benar']} | salah={stats['salah']} | akurasi={akurasi:.2f} | durasi={durasi_latihan:.2f}s")

#     # Reset
#     session.update({
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "active_model_type": "main"
#     })

# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time

# # =======================================================
# # 🚀 ULTIMATE FIX: MONKEY PATCHING LSTM
# # Membajak core TensorFlow secara global agar membuang
# # argumen 'time_major' dari layer manapun (termasuk BiLSTM)
# # =======================================================
# original_lstm_init = tf.keras.layers.LSTM.__init__

# def patched_lstm_init(self, *args, **kwargs):
#     kwargs.pop("time_major", None)
#     original_lstm_init(self, *args, **kwargs)

# tf.keras.layers.LSTM.__init__ = patched_lstm_init
# # =======================================================

# # --- 1. PATH MODEL MAIN ---
# MODEL_PATH = "./lstm/cobaLagi/pose_model_lstm.h5"
# # MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# # LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"
# LABELS_PATH = "./lstm/cobaLagi/labels_lstm_lutut1.txt"
# VALID_THRESHOLD = 0.7

# # --- 2. PATH MODEL SPECIALIST ---
# MODEL_PATH_SPE = "./lstm/coba_rabu_23/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_SPE = "./lstm/coba_rabu_23/labels_lstm_spesial_2.txt"
# SPECIALIST_THRESHOLD = 0.7 

# # --- 3. PATH MODEL BILSTM ---
# MODEL_PATH_BILSTM = "./lstm/cobaLagi/pose_model_bilstm.h5"
# LABELS_PATH_BILSTM = "./lstm/cobaLagi/labels_lstm_lutut.txt"
# BILSTM_THRESHOLD = 0.7

# SEQ_LEN = 20
# FEATURE_COUNT = 132

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []

# specialist_model = None
# specialist_labels = []

# bilstm_model = None
# bilstm_labels = []

# sessions = {}

# SPECIALIST_TARGETS = {
#     # "ankle alphabet exercise",
#     # "calf raises",
#     # "towel toe curl",
# }


# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )


# # ===============================
# # LOAD MODEL + LABELS
# # ===============================
# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     # Karena kita sudah me-monkey patch TensorFlow di atas,
#     # kita tidak perlu lagi menggunakan custom_objects di sini.
#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded")
#     print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
#     print(f"📌 {model_name} labels:", loaded_labels)
    
#     return loaded_model, loaded_labels


# def load_pose_model():
#     global model, labels, specialist_model, specialist_labels, bilstm_model, bilstm_labels

#     try:
#         model, labels = load_model_and_labels(MODEL_PATH, LABELS_PATH, "MAIN MODEL")
#     except Exception as e:
#         print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
#         model = None; labels = []

#     try:
#         specialist_model, specialist_labels = load_model_and_labels(MODEL_PATH_SPE, LABELS_PATH_SPE, "SPECIALIST MODEL")
#     except Exception as e:
#         print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
#         specialist_model = None; specialist_labels = []

#     try:
#         bilstm_model, bilstm_labels = load_model_and_labels(MODEL_PATH_BILSTM, LABELS_PATH_BILSTM, "BILSTM MODEL")
#     except Exception as e:
#         print("⚠️ BILSTM MODEL LOAD ERROR:", e)
#         bilstm_model = None; bilstm_labels = []


# def select_model(expected_label, active_model_type="main"):
#     expected = normalize_label(expected_label)

#     if expected in SPECIALIST_TARGETS and active_model_type == "main":
#         active_model_type = "specialist"

#     if active_model_type == "specialist" and specialist_model is not None and len(specialist_labels) > 0:
#         return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"
    
#     elif active_model_type == "bilstm" and bilstm_model is not None and len(bilstm_labels) > 0:
#         return bilstm_model, bilstm_labels, BILSTM_THRESHOLD, "bilstm"
    
#     return model, labels, VALID_THRESHOLD, "main"

# load_pose_model()


# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "active_model_type": "main" 
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
#     data = data or {}

#     expected = data.get("expectedLabel") or data.get("expected_label") or data.get("label") or data.get("nama_latihan") or ""
#     normalized_expected = normalize_label(expected)

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": normalized_expected,
#         "start_time": time.time(),
#         "consecutive_errors": 0,
#         "active_model_type": "main" 
#     }

#     print(f"[START] {sid} | target: {normalized_expected}")
#     emit("session_started", {"expected_label": normalized_expected})


# # ===============================
# # RECEIVE & PREDICT
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     sequence_buffer = data.get("landmarks")

#     if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0: return
#     if not isinstance(sequence_buffer[0], list): return
#     if len(sequence_buffer) != SEQ_LEN: return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)
    
#     active_model_type = session.get("active_model_type", "main")

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm, active_model_type)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([sequence_buffer], dtype=np.float32)
#         if np.sum(np.abs(input_tensor)) < 1e-5:
#             emit("inference_result", {
#                 "label": "Tidak terdeteksi",
#                 "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
#                 "feedback": "Pastikan seluruh tubuh masuk ke kamera!",
#                 "active_model": model_name
#             })
#             return 

#         if np.var(input_tensor) < 1e-4:
#             emit("inference_result", {
#                 "label": "Standby",
#                 "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
#                 "feedback": "Ayo mulai bergerak!",
#                 "active_model": model_name
#             })
#             return 
        
#         prediction = selected_model.predict(input_tensor, verbose=0)[0]
#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         # ===============================
#         # UPDATE STATS & ROTASI MODEL
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#             session["consecutive_errors"] = 0
#         else:
#             session["stats"]["salah"] += 1
#             session["consecutive_errors"] += 1

#             # Rotasi 3 model jika salah 3x beruntun
#             if session["consecutive_errors"] >= 3:
#                 current_type = session["active_model_type"]
                
#                 # URUTAN: Main -> BiLSTM -> Specialist -> Main
#                 if current_type == "main":
#                     next_type = "bilstm"
#                 elif current_type == "bilstm":
#                     next_type = "specialist"
#                 else: 
#                     next_type = "main"

#                 session["active_model_type"] = next_type
#                 session["consecutive_errors"] = 0 
                
#                 print(f"⚠️ [WARNING] {sid} salah 3x beruntun! Pindah mode dari {current_type} -> {next_type}.")

#         print(
#             f"🧠 PREDICT BATCH | model={model_name} | "
#             f"pred={predicted_label} | expected={expected_norm} | "
#             f"conf={confidence:.2f} | match={is_match} | "
#             f"Salah beruntun={session['consecutive_errors']}"
#         )

#         emit("inference_result", {
#             "label": predicted_label if is_correct else "Gerakan salah", 
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#             "active_model": model_name
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid
#     if sid not in sessions: return

#     session = sessions[sid]
#     stats = session["stats"]
#     total = stats["benar"] + stats["salah"]
#     akurasi = ((stats["benar"] / total) * 100) if total > 0 else 0.0
#     durasi_latihan = time.time() - session["start_time"] if session.get("start_time") else 0.0

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(f"📊 [SUMMARY] sid={sid} | benar={stats['benar']} | salah={stats['salah']} | akurasi={akurasi:.2f} | durasi={durasi_latihan:.2f}s")

#     # Reset
#     session.update({
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "active_model_type": "main"
#     })


# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time

# # =======================================================
# # 🚀 ULTIMATE FIX: MONKEY PATCHING LSTM
# # Membajak core TensorFlow secara global agar membuang
# # argumen 'time_major' dari layer manapun (termasuk BiLSTM)
# # =======================================================
# original_lstm_init = tf.keras.layers.LSTM.__init__

# def patched_lstm_init(self, *args, **kwargs):
#     kwargs.pop("time_major", None)
#     original_lstm_init(self, *args, **kwargs)

# tf.keras.layers.LSTM.__init__ = patched_lstm_init
# # =======================================================

# # --- 1. PATH MODEL MAIN ---
# MODEL_PATH = "./lstm/cobaLagi/pose_model_lstm.h5"
# # MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# # LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"
# LABELS_PATH = "./lstm/cobaLagi/labels_lstm_lutut1.txt"
# VALID_THRESHOLD = 0.7

# # --- 2. PATH MODEL SPECIALIST ---
# MODEL_PATH_SPE = "./lstm/coba_rabu_23/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_SPE = "./lstm/coba_rabu_23/labels_lstm_spesial_2.txt"
# SPECIALIST_THRESHOLD = 0.7

# # --- 3. PATH MODEL BILSTM ---
# MODEL_PATH_BILSTM = "./lstm/cobaLagi/pose_model_bilstm.h5"
# LABELS_PATH_BILSTM = "./lstm/cobaLagi/labels_lstm_lutut.txt"
# BILSTM_THRESHOLD = 0.7

# # --- 4. PATH MODEL CALF RAISES (KHUSUS) ---
# # TODO: sesuaikan path ini dengan lokasi file model & labels calf raises kamu
# MODEL_PATH_CALF = "./lstm/coba_minggu_28/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_CALF = "./lstm/coba_minggu_28/labels_lstm_spesial_2.txt"
# CALF_THRESHOLD = 0.7

# SEQ_LEN = 20
# FEATURE_COUNT = 132

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []

# specialist_model = None
# specialist_labels = []

# bilstm_model = None
# bilstm_labels = []

# calf_model = None
# calf_labels = []

# sessions = {}

# # Label yang tetap mengikuti mekanisme rotasi 3-model (main -> bilstm -> specialist)
# # jika terus salah
# SPECIALIST_TARGETS = {
#     # "ankle alphabet exercise",
#     # "towel toe curl",
# }

# # Label yang WAJIB selalu ditembak ke model khusus (calf_model),
# # tidak peduli state rotasi/model aktif sesi saat itu
# CALF_TARGETS = {
#     "calf raises",
# }


# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )


# # ===============================
# # LOAD MODEL + LABELS
# # ===============================
# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     # Karena kita sudah me-monkey patch TensorFlow di atas,
#     # kita tidak perlu lagi menggunakan custom_objects di sini.
#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded")
#     print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
#     print(f"📌 {model_name} labels:", loaded_labels)

#     return loaded_model, loaded_labels


# def load_pose_model():
#     global model, labels, specialist_model, specialist_labels, bilstm_model, bilstm_labels, calf_model, calf_labels

#     try:
#         model, labels = load_model_and_labels(MODEL_PATH, LABELS_PATH, "MAIN MODEL")
#     except Exception as e:
#         print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
#         model = None; labels = []

#     try:
#         specialist_model, specialist_labels = load_model_and_labels(MODEL_PATH_SPE, LABELS_PATH_SPE, "SPECIALIST MODEL")
#     except Exception as e:
#         print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
#         specialist_model = None; specialist_labels = []

#     try:
#         bilstm_model, bilstm_labels = load_model_and_labels(MODEL_PATH_BILSTM, LABELS_PATH_BILSTM, "BILSTM MODEL")
#     except Exception as e:
#         print("⚠️ BILSTM MODEL LOAD ERROR:", e)
#         bilstm_model = None; bilstm_labels = []

#     try:
#         calf_model, calf_labels = load_model_and_labels(MODEL_PATH_CALF, LABELS_PATH_CALF, "CALF RAISES MODEL")
#     except Exception as e:
#         print("⚠️ CALF RAISES MODEL LOAD ERROR:", e)
#         calf_model = None; calf_labels = []


# def select_model(expected_label, active_model_type="main"):
#     expected = normalize_label(expected_label)

#     # 0) Paksa ke model khusus calf raises, apapun state rotasi/model aktif sekarang.
#     #    Dicek paling awal supaya tidak pernah "terselip" oleh rotasi main->bilstm->specialist.
#     if expected in CALF_TARGETS and calf_model is not None and len(calf_labels) > 0:
#         return calf_model, calf_labels, CALF_THRESHOLD, "calf"

#     if expected in SPECIALIST_TARGETS and active_model_type == "main":
#         active_model_type = "specialist"

#     if active_model_type == "specialist" and specialist_model is not None and len(specialist_labels) > 0:
#         return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"

#     elif active_model_type == "bilstm" and bilstm_model is not None and len(bilstm_labels) > 0:
#         return bilstm_model, bilstm_labels, BILSTM_THRESHOLD, "bilstm"

#     return model, labels, VALID_THRESHOLD, "main"

# load_pose_model()


# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "active_model_type": "main"
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
#     data = data or {}

#     expected = data.get("expectedLabel") or data.get("expected_label") or data.get("label") or data.get("nama_latihan") or ""
#     normalized_expected = normalize_label(expected)

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": normalized_expected,
#         "start_time": time.time(),
#         "consecutive_errors": 0,
#         "active_model_type": "main"
#     }

#     print(f"[START] {sid} | target: {normalized_expected}")
#     emit("session_started", {"expected_label": normalized_expected})


# # ===============================
# # RECEIVE & PREDICT
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     sequence_buffer = data.get("landmarks")

#     if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0: return
#     if not isinstance(sequence_buffer[0], list): return
#     if len(sequence_buffer) != SEQ_LEN: return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)

#     active_model_type = session.get("active_model_type", "main")

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm, active_model_type)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([sequence_buffer], dtype=np.float32)
#         if np.sum(np.abs(input_tensor)) < 1e-5:
#             emit("inference_result", {
#                 "label": "Tidak terdeteksi",
#                 "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
#                 "feedback": "Pastikan seluruh tubuh masuk ke kamera!",
#                 "active_model": model_name
#             })
#             return

#         if np.var(input_tensor) < 1e-4:
#             emit("inference_result", {
#                 "label": "Standby",
#                 "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
#                 "feedback": "Ayo mulai bergerak!",
#                 "active_model": model_name
#             })
#             return

#         prediction = selected_model.predict(input_tensor, verbose=0)[0]
#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         # ===============================
#         # UPDATE STATS & ROTASI MODEL
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#             session["consecutive_errors"] = 0
#         else:
#             session["stats"]["salah"] += 1
#             session["consecutive_errors"] += 1

#             # Rotasi 3 model jika salah 3x beruntun.
#             # Catatan: rotasi ini diabaikan untuk label yang ada di CALF_TARGETS,
#             # karena select_model() sudah mengunci label tsb ke calf_model duluan.
#             if session["consecutive_errors"] >= 3:
#                 current_type = session["active_model_type"]

#                 # URUTAN: Main -> BiLSTM -> Specialist -> Main
#                 if current_type == "main":
#                     next_type = "bilstm"
#                 elif current_type == "bilstm":
#                     next_type = "specialist"
#                 else:
#                     next_type = "main"

#                 session["active_model_type"] = next_type
#                 session["consecutive_errors"] = 0

#                 print(f"⚠️ [WARNING] {sid} salah 3x beruntun! Pindah mode dari {current_type} -> {next_type}.")

#         print(
#             f"🧠 PREDICT BATCH | model={model_name} | "
#             f"pred={predicted_label} | expected={expected_norm} | "
#             f"conf={confidence:.2f} | match={is_match} | "
#             f"Salah beruntun={session['consecutive_errors']}"
#         )

#         emit("inference_result", {
#             "label": predicted_label if is_correct else "Gerakan salah",
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#             "active_model": model_name
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid
#     if sid not in sessions: return

#     session = sessions[sid]
#     stats = session["stats"]
#     total = stats["benar"] + stats["salah"]
#     akurasi = ((stats["benar"] / total) * 100) if total > 0 else 0.0
#     durasi_latihan = time.time() - session["start_time"] if session.get("start_time") else 0.0

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(f"📊 [SUMMARY] sid={sid} | benar={stats['benar']} | salah={stats['salah']} | akurasi={akurasi:.2f} | durasi={durasi_latihan:.2f}s")

#     # Reset
#     session.update({
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "active_model_type": "main"
#     })



# from flask import request
# from flask_socketio import emit
# from extensions import socketio
# import numpy as np
# import tensorflow as tf
# import os
# import time

# # =======================================================
# # 🚀 ULTIMATE FIX: MONKEY PATCHING LSTM
# # Membajak core TensorFlow secara global agar membuang
# # argumen 'time_major' dari layer manapun (termasuk BiLSTM)
# # =======================================================
# original_lstm_init = tf.keras.layers.LSTM.__init__

# def patched_lstm_init(self, *args, **kwargs):
#     kwargs.pop("time_major", None)
#     original_lstm_init(self, *args, **kwargs)

# tf.keras.layers.LSTM.__init__ = patched_lstm_init
# # =======================================================

# # --- 1. PATH MODEL MAIN ---
# MODEL_PATH = "./lstm/cobaLagi/pose_model_lstm.h5"
# # MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
# # LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"
# LABELS_PATH = "./lstm/cobaLagi/labels_lstm_lutut1.txt"
# VALID_THRESHOLD = 0.7

# # --- 2. PATH MODEL SPECIALIST ---
# MODEL_PATH_SPE = "./lstm/coba_rabu_23/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_SPE = "./lstm/coba_rabu_23/labels_lstm_spesial_2.txt"
# SPECIALIST_THRESHOLD = 0.7

# # --- 3. PATH MODEL BILSTM ---
# MODEL_PATH_BILSTM = "./lstm/cobaLagi/pose_model_bilstm.h5"
# LABELS_PATH_BILSTM = "./lstm/cobaLagi/labels_lstm_lutut.txt"
# BILSTM_THRESHOLD = 0.7

# # --- 4. PATH MODEL CALF RAISES (KHUSUS) ---
# # TODO: sesuaikan path ini dengan lokasi file model & labels calf raises kamu
# MODEL_PATH_CALF = "./lstm/coba_minggu_28/pose_model_lstm_spesial_2.h5"
# LABELS_PATH_CALF = "./lstm/coba_minggu_28/labels_lstm_spesial_2.txt"
# CALF_THRESHOLD = 0.7

# SEQ_LEN = 20
# FEATURE_COUNT = 132

# # ===============================
# # GLOBAL STATE
# # ===============================
# model = None
# labels = []

# specialist_model = None
# specialist_labels = []

# bilstm_model = None
# bilstm_labels = []

# calf_model = None
# calf_labels = []

# sessions = {}

# # Label yang tetap mengikuti mekanisme rotasi 3-model (main -> bilstm -> specialist)
# # jika terus salah
# SPECIALIST_TARGETS = {
#     # "ankle alphabet exercise",
#     # "towel toe curl",
# }

# # Label yang model AWAL/utamanya adalah calf_model, tapi tetap boleh
# # berotasi ke model lain kalau terus salah (tidak dikunci permanen)
# CALF_TARGETS = {
#     "calf raises",
# }

# # ===============================
# # URUTAN ROTASI MODEL
# # ===============================
# # Exercise biasa: main -> bilstm -> specialist -> main -> ...
# ROTATION_ORDER_DEFAULT = ["main", "bilstm", "specialist"]

# # Calf raises: mulai dari calf (paling relevan), lalu ikut muter ke
# # model lain kalau terus salah, baru balik lagi ke calf
# ROTATION_ORDER_CALF = ["calf", "bilstm", "specialist", "main"]


# def get_rotation_order(expected_norm):
#     if expected_norm in CALF_TARGETS:
#         return ROTATION_ORDER_CALF
#     return ROTATION_ORDER_DEFAULT


# def get_initial_model_type(expected_norm):
#     """Model type yang dipakai pertama kali saat sesi/exercise dimulai."""
#     if expected_norm in CALF_TARGETS and calf_model is not None and len(calf_labels) > 0:
#         return "calf"
#     return "main"


# def normalize_label(value):
#     return (
#         str(value)
#         .lower()
#         .replace("_", " ")
#         .replace("-", " ")
#         .strip()
#     )


# # ===============================
# # LOAD MODEL + LABELS
# # ===============================
# def load_model_and_labels(model_path, labels_path, model_name):
#     print(f"🔧 Loading {model_name}: {model_path}")

#     # Karena kita sudah me-monkey patch TensorFlow di atas,
#     # kita tidak perlu lagi menggunakan custom_objects di sini.
#     loaded_model = tf.keras.models.load_model(
#         model_path,
#         compile=False
#     )

#     if not os.path.exists(labels_path):
#         raise FileNotFoundError(f"Labels file not found: {labels_path}")

#     with open(labels_path, "r", encoding="utf-8") as f:
#         loaded_labels = [normalize_label(line) for line in f if line.strip()]

#     if len(loaded_labels) == 0:
#         raise ValueError(f"Labels file empty: {labels_path}")

#     print(f"✅ {model_name} loaded")
#     print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
#     print(f"📌 {model_name} labels:", loaded_labels)

#     return loaded_model, loaded_labels


# def load_pose_model():
#     global model, labels, specialist_model, specialist_labels, bilstm_model, bilstm_labels, calf_model, calf_labels

#     try:
#         model, labels = load_model_and_labels(MODEL_PATH, LABELS_PATH, "MAIN MODEL")
#     except Exception as e:
#         print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
#         model = None; labels = []

#     try:
#         specialist_model, specialist_labels = load_model_and_labels(MODEL_PATH_SPE, LABELS_PATH_SPE, "SPECIALIST MODEL")
#     except Exception as e:
#         print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
#         specialist_model = None; specialist_labels = []

#     try:
#         bilstm_model, bilstm_labels = load_model_and_labels(MODEL_PATH_BILSTM, LABELS_PATH_BILSTM, "BILSTM MODEL")
#     except Exception as e:
#         print("⚠️ BILSTM MODEL LOAD ERROR:", e)
#         bilstm_model = None; bilstm_labels = []

#     try:
#         calf_model, calf_labels = load_model_and_labels(MODEL_PATH_CALF, LABELS_PATH_CALF, "CALF RAISES MODEL")
#     except Exception as e:
#         print("⚠️ CALF RAISES MODEL LOAD ERROR:", e)
#         calf_model = None; calf_labels = []


# def select_model(expected_label, active_model_type="main"):
#     expected = normalize_label(expected_label)

#     if expected in SPECIALIST_TARGETS and active_model_type == "main":
#         active_model_type = "specialist"

#     if active_model_type == "calf" and calf_model is not None and len(calf_labels) > 0:
#         return calf_model, calf_labels, CALF_THRESHOLD, "calf"

#     if active_model_type == "specialist" and specialist_model is not None and len(specialist_labels) > 0:
#         return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"

#     elif active_model_type == "bilstm" and bilstm_model is not None and len(bilstm_labels) > 0:
#         return bilstm_model, bilstm_labels, BILSTM_THRESHOLD, "bilstm"

#     return model, labels, VALID_THRESHOLD, "main"

# load_pose_model()


# # ===============================
# # CONNECT
# # ===============================
# @socketio.on("connect")
# def handle_connect():
#     sid = request.sid

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "active_model_type": "main"
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
#     data = data or {}

#     expected = data.get("expectedLabel") or data.get("expected_label") or data.get("label") or data.get("nama_latihan") or ""
#     normalized_expected = normalize_label(expected)

#     initial_model_type = get_initial_model_type(normalized_expected)

#     sessions[sid] = {
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": normalized_expected,
#         "start_time": time.time(),
#         "consecutive_errors": 0,
#         "active_model_type": initial_model_type
#     }

#     print(f"[START] {sid} | target: {normalized_expected} | model awal: {initial_model_type}")
#     emit("session_started", {"expected_label": normalized_expected})


# # ===============================
# # RECEIVE & PREDICT
# # ===============================
# @socketio.on("send_pose_data")
# def handle_pose_data(data):
#     sid = request.sid

#     if sid not in sessions:
#         return

#     session = sessions[sid]
#     sequence_buffer = data.get("landmarks")

#     if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0: return
#     if not isinstance(sequence_buffer[0], list): return
#     if len(sequence_buffer) != SEQ_LEN: return

#     expected = session.get("expected_label") or ""
#     expected_norm = normalize_label(expected)

#     active_model_type = session.get("active_model_type", "main")

#     selected_model, selected_labels, threshold, model_name = select_model(expected_norm, active_model_type)

#     if selected_model is None or len(selected_labels) == 0:
#         print("❌ Model/labels kosong")
#         return

#     try:
#         input_tensor = np.array([sequence_buffer], dtype=np.float32)
#         if np.sum(np.abs(input_tensor)) < 1e-5:
#             emit("inference_result", {
#                 "label": "Tidak terdeteksi",
#                 "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
#                 "feedback": "Pastikan seluruh tubuh masuk ke kamera!",
#                 "active_model": model_name
#             })
#             return

#         if np.var(input_tensor) < 1e-4:
#             emit("inference_result", {
#                 "label": "Standby",
#                 "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
#                 "feedback": "Ayo mulai bergerak!",
#                 "active_model": model_name
#             })
#             return

#         prediction = selected_model.predict(input_tensor, verbose=0)[0]
#         max_idx = int(np.argmax(prediction))
#         confidence = float(prediction[max_idx])

#         raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
#         predicted_label = normalize_label(raw_label)

#         is_match = predicted_label == expected_norm
#         is_valid = confidence >= threshold
#         is_correct = is_match and is_valid

#         # ===============================
#         # UPDATE STATS & ROTASI MODEL
#         # ===============================
#         if is_correct:
#             session["stats"]["benar"] += 1
#             session["consecutive_errors"] = 0
#         else:
#             session["stats"]["salah"] += 1
#             session["consecutive_errors"] += 1

#             # Rotasi model jika salah 3x beruntun.
#             # Urutan rotasi tergantung jenis exercise:
#             #   - calf raises  : calf -> bilstm -> specialist -> main -> calf -> ...
#             #   - exercise lain: main -> bilstm -> specialist -> main -> ...
#             if session["consecutive_errors"] >= 3:
#                 current_type = session["active_model_type"]
#                 rotation_order = get_rotation_order(expected_norm)

#                 if current_type in rotation_order:
#                     current_idx = rotation_order.index(current_type)
#                     next_type = rotation_order[(current_idx + 1) % len(rotation_order)]
#                 else:
#                     # fallback kalau current_type di luar urutan yang berlaku
#                     next_type = rotation_order[0]

#                 session["active_model_type"] = next_type
#                 session["consecutive_errors"] = 0

#                 print(f"⚠️ [WARNING] {sid} salah 3x beruntun! Pindah mode dari {current_type} -> {next_type}.")

#         print(
#             f"🧠 PREDICT BATCH | model={model_name} | "
#             f"pred={predicted_label} | expected={expected_norm} | "
#             f"conf={confidence:.2f} | match={is_match} | "
#             f"Salah beruntun={session['consecutive_errors']}"
#         )

#         emit("inference_result", {
#             "label": predicted_label if is_correct else "Gerakan salah",
#             "confidence": confidence,
#             "is_valid": is_valid,
#             "is_match": is_match,
#             "is_correct": is_correct,
#             "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
#             "active_model": model_name
#         })

#     except Exception as e:
#         print("❌ [ERROR] inference error:", e)


# # ===============================
# # END EXERCISE
# # ===============================
# @socketio.on("end_exercise")
# def handle_end_exercise():
#     sid = request.sid
#     if sid not in sessions: return

#     session = sessions[sid]
#     stats = session["stats"]
#     total = stats["benar"] + stats["salah"]
#     akurasi = ((stats["benar"] / total) * 100) if total > 0 else 0.0
#     durasi_latihan = time.time() - session["start_time"] if session.get("start_time") else 0.0

#     emit("exercise_summary", {
#         "total_benar": stats["benar"],
#         "total_salah": stats["salah"],
#         "akurasi": akurasi,
#         "durasi_latihan": durasi_latihan
#     })

#     print(f"📊 [SUMMARY] sid={sid} | benar={stats['benar']} | salah={stats['salah']} | akurasi={akurasi:.2f} | durasi={durasi_latihan:.2f}s")

#     # Reset
#     session.update({
#         "buffer": [],
#         "stats": {"benar": 0, "salah": 0},
#         "expected_label": "",
#         "start_time": None,
#         "consecutive_errors": 0,
#         "active_model_type": "main"
#     })


from flask import request
from flask_socketio import emit
from extensions import socketio
import numpy as np
import tensorflow as tf
import os
import time

# =======================================================
# 🚀 ULTIMATE FIX: MONKEY PATCHING LSTM
# Membajak core TensorFlow secara global agar membuang
# argumen 'time_major' dari layer manapun (termasuk BiLSTM)
# =======================================================
original_lstm_init = tf.keras.layers.LSTM.__init__

def patched_lstm_init(self, *args, **kwargs):
    kwargs.pop("time_major", None)
    original_lstm_init(self, *args, **kwargs)

tf.keras.layers.LSTM.__init__ = patched_lstm_init
# =======================================================

# --- 1. PATH MODEL MAIN ---
# MODEL_PATH = "./lstm/cobaLagi/pose_model_lstm.h5"
MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"
# LABELS_PATH = "./lstm/cobaLagi/labels_lstm_lutut1.txt"
VALID_THRESHOLD = 0.7

# --- 2. PATH MODEL SPECIALIST ---
MODEL_PATH_SPE =  "./lstm/coba_selasa_16/pose_model1.h5"
LABELS_PATH_SPE = "./lstm/coba_selasa_16/labels_lstm_lutut.txt"
SPECIALIST_THRESHOLD = 0.7

# --- 3. PATH MODEL BILSTM ---
MODEL_PATH_BILSTM = "./lstm/coba_selasa_16/pose_model1.h5"
LABELS_PATH_BILSTM = "./lstm/coba_selasa_16/labels_lstm_lutut.txt"
BILSTM_THRESHOLD = 0.7

# --- 4. PATH MODEL CALF RAISES (KHUSUS) ---
# TODO: sesuaikan path ini dengan lokasi file model & labels calf raises kamu
MODEL_PATH_CALF = "./lstm/coba_minggu_28/pose_model_lstm_spesial_2.h5"
LABELS_PATH_CALF = "./lstm/coba_minggu_28/labels_lstm_spesial_2.txt"
CALF_THRESHOLD = 0.7

SEQ_LEN = 20
FEATURE_COUNT = 132

# ===============================
# GLOBAL STATE
# ===============================
model = None
labels = []

specialist_model = None
specialist_labels = []

bilstm_model = None
bilstm_labels = []

calf_model = None
calf_labels = []

sessions = {}

# Label yang tetap mengikuti mekanisme rotasi 3-model (main -> bilstm -> specialist)
# jika terus salah
SPECIALIST_TARGETS = {
    # "ankle alphabet exercise",
    # "towel toe curl",
}

# Label yang ikut menyertakan calf_model dalam rotasi (tidak dikunci permanen,
# dan bukan model awal juga -- lihat ROTATION_ORDER_CALF di bawah)
CALF_TARGETS = {
    "calf raises",
}

# ===============================
# URUTAN ROTASI MODEL
# ===============================
# Exercise biasa: main -> bilstm -> specialist -> main -> ...
ROTATION_ORDER_DEFAULT = ["main", "bilstm", "specialist"]

# Calf raises: TETAP mulai dari main seperti exercise lain, muter dulu
# ke bilstm, baru dapat giliran calf_model, lalu specialist, baru balik ke main.
# Jadi calf_model bukan default/awal, tapi tetap kebagian giliran setelah 1-2x rotasi.
ROTATION_ORDER_CALF = ["main", "bilstm", "calf", "specialist"]


def get_rotation_order(expected_norm):
    if expected_norm in CALF_TARGETS:
        return ROTATION_ORDER_CALF
    return ROTATION_ORDER_DEFAULT


def normalize_label(value):
    return (
        str(value)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )


# ===============================
# LOAD MODEL + LABELS
# ===============================
def load_model_and_labels(model_path, labels_path, model_name):
    print(f"🔧 Loading {model_name}: {model_path}")

    # Karena kita sudah me-monkey patch TensorFlow di atas,
    # kita tidak perlu lagi menggunakan custom_objects di sini.
    loaded_model = tf.keras.models.load_model(
        model_path,
        compile=False
    )

    if not os.path.exists(labels_path):
        raise FileNotFoundError(f"Labels file not found: {labels_path}")

    with open(labels_path, "r", encoding="utf-8") as f:
        loaded_labels = [normalize_label(line) for line in f if line.strip()]

    if len(loaded_labels) == 0:
        raise ValueError(f"Labels file empty: {labels_path}")

    print(f"✅ {model_name} loaded")
    print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
    print(f"📌 {model_name} labels:", loaded_labels)

    return loaded_model, loaded_labels


def load_pose_model():
    global model, labels, specialist_model, specialist_labels, bilstm_model, bilstm_labels, calf_model, calf_labels

    try:
        model, labels = load_model_and_labels(MODEL_PATH, LABELS_PATH, "MAIN MODEL")
    except Exception as e:
        print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
        model = None; labels = []

    try:
        specialist_model, specialist_labels = load_model_and_labels(MODEL_PATH_SPE, LABELS_PATH_SPE, "SPECIALIST MODEL")
    except Exception as e:
        print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
        specialist_model = None; specialist_labels = []

    try:
        bilstm_model, bilstm_labels = load_model_and_labels(MODEL_PATH_BILSTM, LABELS_PATH_BILSTM, "BILSTM MODEL")
    except Exception as e:
        print("⚠️ BILSTM MODEL LOAD ERROR:", e)
        bilstm_model = None; bilstm_labels = []

    try:
        calf_model, calf_labels = load_model_and_labels(MODEL_PATH_CALF, LABELS_PATH_CALF, "CALF RAISES MODEL")
    except Exception as e:
        print("⚠️ CALF RAISES MODEL LOAD ERROR:", e)
        calf_model = None; calf_labels = []


def select_model(expected_label, active_model_type="main"):
    expected = normalize_label(expected_label)

    if expected in SPECIALIST_TARGETS and active_model_type == "main":
        active_model_type = "specialist"

    if active_model_type == "calf" and calf_model is not None and len(calf_labels) > 0:
        return calf_model, calf_labels, CALF_THRESHOLD, "calf"

    if active_model_type == "specialist" and specialist_model is not None and len(specialist_labels) > 0:
        return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"

    elif active_model_type == "bilstm" and bilstm_model is not None and len(bilstm_labels) > 0:
        return bilstm_model, bilstm_labels, BILSTM_THRESHOLD, "bilstm"

    return model, labels, VALID_THRESHOLD, "main"

load_pose_model()


# ===============================
# CONNECT
# ===============================
@socketio.on("connect")
def handle_connect():
    sid = request.sid

    sessions[sid] = {
        "buffer": [],
        "stats": {"benar": 0, "salah": 0},
        "expected_label": "",
        "start_time": None,
        "consecutive_errors": 0,
        "active_model_type": "main"
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
    data = data or {}

    expected = data.get("expectedLabel") or data.get("expected_label") or data.get("label") or data.get("nama_latihan") or ""
    normalized_expected = normalize_label(expected)

    sessions[sid] = {
        "buffer": [],
        "stats": {"benar": 0, "salah": 0},
        "expected_label": normalized_expected,
        "start_time": time.time(),
        "consecutive_errors": 0,
        "active_model_type": "main"
    }

    print(f"[START] {sid} | target: {normalized_expected}")
    emit("session_started", {"expected_label": normalized_expected})


# ===============================
# RECEIVE & PREDICT
# ===============================
@socketio.on("send_pose_data")
def handle_pose_data(data):
    sid = request.sid

    if sid not in sessions:
        return

    session = sessions[sid]
    sequence_buffer = data.get("landmarks")

    if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0: return
    if not isinstance(sequence_buffer[0], list): return
    if len(sequence_buffer) != SEQ_LEN: return

    expected = session.get("expected_label") or ""
    expected_norm = normalize_label(expected)

    active_model_type = session.get("active_model_type", "main")

    selected_model, selected_labels, threshold, model_name = select_model(expected_norm, active_model_type)

    if selected_model is None or len(selected_labels) == 0:
        print("❌ Model/labels kosong")
        return

    try:
        input_tensor = np.array([sequence_buffer], dtype=np.float32)
        if np.sum(np.abs(input_tensor)) < 1e-5:
            emit("inference_result", {
                "label": "Tidak terdeteksi",
                "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
                "feedback": "Pastikan seluruh tubuh masuk ke kamera!",
                "active_model": model_name
            })
            return

        if np.var(input_tensor) < 1e-4:
            emit("inference_result", {
                "label": "Standby",
                "confidence": 0.0, "is_valid": False, "is_match": False, "is_correct": False,
                "feedback": "Ayo mulai bergerak!",
                "active_model": model_name
            })
            return

        prediction = selected_model.predict(input_tensor, verbose=0)[0]
        max_idx = int(np.argmax(prediction))
        confidence = float(prediction[max_idx])

        raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
        predicted_label = normalize_label(raw_label)

        is_match = predicted_label == expected_norm
        is_valid = confidence >= threshold
        is_correct = is_match and is_valid

        # ===============================
        # UPDATE STATS & ROTASI MODEL
        # ===============================
        if is_correct:
            session["stats"]["benar"] += 1
            session["consecutive_errors"] = 0
        else:
            session["stats"]["salah"] += 1
            session["consecutive_errors"] += 1

            # Rotasi model jika salah 3x beruntun.
            # Urutan rotasi tergantung jenis exercise:
            #   - calf raises  : main -> bilstm -> calf -> specialist -> main -> ...
            #   - exercise lain: main -> bilstm -> specialist -> main -> ...
            if session["consecutive_errors"] >= 3:
                current_type = session["active_model_type"]
                rotation_order = get_rotation_order(expected_norm)

                if current_type in rotation_order:
                    current_idx = rotation_order.index(current_type)
                    next_type = rotation_order[(current_idx + 1) % len(rotation_order)]
                else:
                    # fallback kalau current_type di luar urutan yang berlaku
                    next_type = rotation_order[0]

                session["active_model_type"] = next_type
                session["consecutive_errors"] = 0

                print(f"⚠️ [WARNING] {sid} salah 3x beruntun! Pindah mode dari {current_type} -> {next_type}.")

        print(
            f"🧠 PREDICT BATCH | model={model_name} | "
            f"pred={predicted_label} | expected={expected_norm} | "
            f"conf={confidence:.2f} | match={is_match} | "
            f"Salah beruntun={session['consecutive_errors']}"
        )

        emit("inference_result", {
            "label": predicted_label if is_correct else "Gerakan salah",
            "confidence": confidence,
            "is_valid": is_valid,
            "is_match": is_match,
            "is_correct": is_correct,
            "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
            "active_model": model_name
        })

    except Exception as e:
        print("❌ [ERROR] inference error:", e)


# ===============================
# END EXERCISE
# ===============================
@socketio.on("end_exercise")
def handle_end_exercise():
    sid = request.sid
    if sid not in sessions: return

    session = sessions[sid]
    stats = session["stats"]
    total = stats["benar"] + stats["salah"]
    akurasi = ((stats["benar"] / total) * 100) if total > 0 else 0.0
    durasi_latihan = time.time() - session["start_time"] if session.get("start_time") else 0.0

    emit("exercise_summary", {
        "total_benar": stats["benar"],
        "total_salah": stats["salah"],
        "akurasi": akurasi,
        "durasi_latihan": durasi_latihan
    })

    print(f"📊 [SUMMARY] sid={sid} | benar={stats['benar']} | salah={stats['salah']} | akurasi={akurasi:.2f} | durasi={durasi_latihan:.2f}s")

    # Reset
    session.update({
        "buffer": [],
        "stats": {"benar": 0, "salah": 0},
        "expected_label": "",
        "start_time": None,
        "consecutive_errors": 0,
        "active_model_type": "main"
    })