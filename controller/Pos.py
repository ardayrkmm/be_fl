from flask import request
from flask_socketio import emit
from extensions import socketio
import numpy as np
import tensorflow as tf
import os
import time

# ===============================
# CONFIG
# ===============================
MODEL_PATH = "./lstm/coba_senin_15/pose_model_lstm.h5"
LABELS_PATH = "./lstm/coba_senin_15/labels_lstm_baru.txt"
MODEL_PATH_SPE = "./lstm/coba_senin_15/pose_model_spe.h5"
LABELS_PATH_SPE = "./lstm/coba_senin_15/labels_lstm_spe.txt"



SEQ_LEN = 20
FEATURE_COUNT = 132
VALID_THRESHOLD = 0.7

SPECIALIST_THRESHOLDS = {
    "calf raises": 0.35,
    "straight leg raise": 0.50,
}

SMOOTHING_WINDOW = 5


# ===============================
# GLOBAL STATE
# ===============================
model = None
labels = []
specialist_model = None
specialist_labels = []

sessions = {}

SPECIALIST_TARGETS = {
    "calf raises",
    "straight leg raise",
}


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

def load_model_and_labels(model_path, labels_path, model_name):
    print(f"🔧 Loading {model_name}: {model_path}")

    loaded_model = tf.keras.models.load_model(
        model_path,
        compile=False,
        custom_objects={"LSTM": CustomLSTM}
    )

    if not os.path.exists(labels_path):
        raise FileNotFoundError(f"Labels file not found: {labels_path}")

    with open(labels_path, "r", encoding="utf-8") as f:
        loaded_labels = [normalize_label(line) for line in f if line.strip()]

    if len(loaded_labels) == 0:
        raise ValueError(f"Labels file empty: {labels_path}")

    print(f"✅ {model_name} loaded")
    print(f"✅ {model_name} labels: {len(loaded_labels)} classes")
    print(f"📌 {model_name} sample labels:", loaded_labels[:5])

    return loaded_model, loaded_labels


def normalize_label(value):
    return (
        str(value)
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        .strip()
    )
def get_label_index(label_list, target_label):
    target = normalize_label(target_label)

    for index, label in enumerate(label_list):
        if normalize_label(label) == target:
            return index

    return None

def load_pose_model():
    global model, labels, specialist_model, specialist_labels

    try:
        model, labels = load_model_and_labels(
            MODEL_PATH,
            LABELS_PATH,
            "MAIN MODEL"
        )
    except Exception as e:
        print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
        model = None
        labels = []

    try:
        specialist_model, specialist_labels = load_model_and_labels(
            MODEL_PATH_SPE,
            LABELS_PATH_SPE,
            "SPECIALIST MODEL"
        )
    except Exception as e:
        print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
        specialist_model = None
        specialist_labels = []


def select_model(expected_label):
    expected = normalize_label(expected_label)

    if (
        expected in SPECIALIST_TARGETS
        and specialist_model is not None
        and len(specialist_labels) > 0
    ):
        threshold = SPECIALIST_THRESHOLDS.get(expected, 0.50)
        return specialist_model, specialist_labels, threshold, "specialist"

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
    "stats": {
        "benar": 0,
        "salah": 0
    },
    "expected_label": "",
    "start_time": None,
    "specialist_scores": [],
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
            "stats": {
                "benar": 0,
                "salah": 0
            },
            "expected_label": "",
            "start_time": None
        }

    data = data or {}

    expected = data.get("expectedLabel")
    if expected is None:
        expected = data.get("expected_label")
    if expected is None:
        expected = data.get("label")
    if expected is None:
        expected = data.get("nama_latihan")
    if expected is None:
        expected = ""

    normalized_expected = normalize_label(expected)

    sessions[sid].update({
        "buffer": [],
        "stats": {
            "benar": 0,
            "salah": 0
        },
        "expected_label": normalized_expected,
        "start_time": time.time()
    })

    print(f"[START] {sid} | target: {normalized_expected}")

    emit("session_started", {
        "expected_label": normalized_expected
    })

@socketio.on("send_pose_data")
def handle_pose_data(data):
    sid = request.sid

    if sid not in sessions:
        return

    session = sessions[sid]
    buffer = session["buffer"]

    landmarks = data.get("landmarks")

    if not isinstance(landmarks, list):
        print(f"⚠️ landmarks bukan list | sid={sid}")
        return

    if len(landmarks) != FEATURE_COUNT:
        print(
            f"⚠️ landmarks length salah: {len(landmarks)}, "
            f"expected {FEATURE_COUNT}"
        )
        return

    buffer.append(landmarks)

    if len(buffer) > SEQ_LEN:
        buffer.pop(0)

    if len(buffer) < SEQ_LEN:
        return

    expected = session.get("expected_label") or ""
    expected_norm = normalize_label(expected)

    selected_model, selected_labels, threshold, model_name = select_model(expected_norm)

    if selected_model is None or len(selected_labels) == 0:
        print("❌ Model/labels kosong")
        return

    try:
        input_tensor = np.array([buffer], dtype=np.float32)
        prediction = selected_model.predict(input_tensor, verbose=0)[0]

        # ===============================
        # SPECIALIST MODEL: CALF / STRAIGHT
        # ===============================
        if model_name == "specialist":
            max_idx = int(np.argmax(prediction))
            top_label = normalize_label(selected_labels[max_idx])
            top_confidence = float(prediction[max_idx])

            expected_idx = get_label_index(selected_labels, expected_norm)

            if expected_idx is None:
                print(
                    f"❌ Expected label tidak ada di specialist labels | "
                    f"expected={expected_norm} | labels={selected_labels}"
                )
                return

            expected_score = float(prediction[expected_idx])

            scores = session.setdefault("specialist_scores", [])
            scores.append(expected_score)

            if len(scores) > SMOOTHING_WINDOW:
                scores.pop(0)

            smoothed_score = sum(scores) / len(scores)

            threshold = SPECIALIST_THRESHOLDS.get(expected_norm, 0.50)
            is_correct = smoothed_score >= threshold

            print(
                f"🎯 SPECIALIST | expected={expected_norm} | "
                f"expected_score={expected_score:.4f} | "
                f"smooth={smoothed_score:.4f} | "
                f"threshold={threshold:.2f} | "
                f"top={top_label}:{top_confidence:.4f} | "
                f"correct={is_correct}"
            )

            emit("inference_result", {
                "label": expected_norm if is_correct else "belum sesuai",
                "predicted_label": top_label,
                "confidence": smoothed_score,
                "top_confidence": top_confidence,
                "is_valid": is_correct,
                "is_match": is_correct,
                "is_correct": is_correct,
                "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
                "model_used": model_name,
                "total_benar": session["stats"]["benar"],
                "total_salah": session["stats"]["salah"],
            })
            return

        # ===============================
        # MAIN MODEL
        # ===============================
        max_idx = int(np.argmax(prediction))
        confidence = float(prediction[max_idx])

        raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
        predicted_label = normalize_label(raw_label)

        is_match = predicted_label == expected_norm
        is_valid = confidence >= threshold
        is_correct = is_match and is_valid

        print(
            f"🧠 MAIN | pred={predicted_label} | "
            f"expected={expected_norm} | "
            f"conf={confidence:.2f} | "
            f"match={is_match}"
        )

        emit("inference_result", {
            "label": predicted_label,
            "confidence": confidence,
            "is_valid": is_valid,
            "is_match": is_match,
            "is_correct": is_correct,
            "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
            "model_used": model_name,
            "total_benar": session["stats"]["benar"],
            "total_salah": session["stats"]["salah"],
        })

    except Exception as e:
        print("❌ [ERROR] inference error:", e)
# 
#  ===============================
# END EXERCISE
# ===============================
@socketio.on("end_exercise")
def handle_end_exercise():
    sid = request.sid

    if sid not in sessions:
        return

    session = sessions[sid]
    stats = session["stats"]

    total = stats["benar"] + stats["salah"]
    akurasi = stats["benar"] / total if total > 0 else 0.0

    durasi_latihan = 0.0
    if session.get("start_time") is not None:
        durasi_latihan = time.time() - session["start_time"]

    emit("exercise_summary", {
        "total_benar": stats["benar"],
        "total_salah": stats["salah"],
        "akurasi": akurasi,
        "durasi_latihan": durasi_latihan
    })

    print(
        f"📊 [SUMMARY] sid={sid} | "
        f"benar={stats['benar']} | "
        f"salah={stats['salah']} | "
        f"akurasi={akurasi:.2f} | "
        f"durasi={durasi_latihan:.2f}s"
    )

    session.update({
        "buffer": [],
        "stats": {
            "benar": 0,
            "salah": 0
        },
        "start_time": None
    })


===============================
SEND POSE DATA - 1 MODEL SAJA
===============================
@socketio.on("send_pose_data")
def handle_pose_data(data):
    sid = request.sid

    if sid not in sessions:
        return

    session = sessions[sid]
    buffer = session["buffer"]

    landmarks = data.get("landmarks")

    if not isinstance(landmarks, list):
        print(f"⚠️ landmarks bukan list | sid={sid}")
        return

    if len(landmarks) != FEATURE_COUNT:
        print(
            f"⚠️ landmarks length salah: {len(landmarks)}, "
            f"expected {FEATURE_COUNT}"
        )
        return

    buffer.append(landmarks)

    if len(buffer) > SEQ_LEN:
        buffer.pop(0)

    if len(buffer) < SEQ_LEN:
        return

    expected = session.get("expected_label") or ""
    expected_norm = normalize_label(expected)

    selected_model, selected_labels, threshold, model_name = select_model(expected_norm)

    if selected_model is None or len(selected_labels) == 0:
        print("❌ Model/labels kosong")
        return

    try:
        input_tensor = np.array([buffer], dtype=np.float32)
        prediction = selected_model.predict(input_tensor, verbose=0)[0]

        max_idx = int(np.argmax(prediction))
        confidence = float(prediction[max_idx])

        raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
        predicted_label = normalize_label(raw_label)

        is_match = predicted_label == expected_norm
        is_valid = confidence >= threshold
        is_correct = is_match and is_valid

        print(
            f"🧠 PREDICT | model={model_name} | "
            f"shape={input_tensor.shape} | "
            f"pred={predicted_label} | "
            f"expected={expected_norm} | "
            f"conf={confidence:.2f} | "
            f"match={is_match}"
        )

        emit("inference_result", {
            
            "label": predicted_label if is_correct else "Gerakan salah", 
            "confidence": confidence,
            "is_valid": is_valid,
            "is_match": is_match,
            "is_correct": is_correct,
            "feedback": "Gerakan benar" if is_correct else "Perbaiki Posisi",
        })

    except Exception as e:
        print("❌ [ERROR] inference error:", e)


from flask import request
from flask_socketio import emit
from extensions import socketio
import numpy as np
import tensorflow as tf
import os
import time

# ===============================
# CONFIG - 1 MODEL SAJA
# ===============================
# MODEL_PATH = "./lstm/coba_rabu_23/pose_model_lstm1.h5"
# LABELS_PATH = "./lstm/coba_rabu_23/labels_lstm_lutut1.txt"
MODEL_PATH = "./lstm/coba_minggu_28/pose_model_lstm1.h5"
LABELS_PATH = "./lstm/coba_minggu_28/labels_lstm_lutut1.txt"

# SEQ_LEN = 20
# FEATURE_COUNT = 132
# VALID_THRESHOLD = 0.7

# MODEL_PATH = "./lstm/pose_model_lstm.h5"
# LABELS_PATH = "./lstm/labels_lstm.txt"

MODEL_PATH_SPE = "./lstm/coba_minggu_28/pose_model_spesial.h5"
LABELS_PATH_SPE = "./lstm/coba_selasa_16/labels_lstm_spesial.txt"
MODEL_PATH_SPE_2 = "./lstm/coba_minggu_28/pose_model_spesial_2.h5"
LABELS_PATH_SPE_2 = "./lstm/coba_selasa_16/labels_lstm_spesial_2.txt"

SEQ_LEN = 30
FEATURE_COUNT = 132
VALID_THRESHOLD = 0.7
SPECIALIST_THRESHOLD = 0.7

# ===============================
# GLOBAL STATE
# ===============================
model = None
labels = []

specialist_model = None
specialist_labels = []

sessions = {}

SPECIALIST_TARGETS = {
    # "ankle alphabet exercise",
    # "calf raises",
    # "towel toe curl",
}

# ===============================
# FIX LSTM COMPATIBILITY
# ===============================
class CustomLSTM(tf.keras.layers.LSTM):
    def __init__(self, *args, **kwargs):
        kwargs.pop("time_major", None)
        super().__init__(*args, **kwargs)


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

    loaded_model = tf.keras.models.load_model(
        model_path,
        compile=False,
        custom_objects={"LSTM": CustomLSTM}
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
    print(f"📌 {model_name} input shape:", loaded_model.input_shape)
    print(f"📌 {model_name} output shape:", loaded_model.output_shape)

    return loaded_model, loaded_labels


def load_pose_model():
    global model, labels, specialist_model, specialist_labels

    try:
        model, labels = load_model_and_labels(
            MODEL_PATH,
            LABELS_PATH,
            "MAIN MODEL"
        )
    except Exception as e:
        print("❌ FATAL MAIN MODEL LOAD ERROR:", e)
        model = None
        labels = []

    try:
        specialist_model, specialist_labels = load_model_and_labels(
            MODEL_PATH_SPE,
            LABELS_PATH_SPE,
            "SPECIALIST MODEL"
        )
    except Exception as e:
        print("⚠️ SPECIALIST MODEL LOAD ERROR:", e)
        specialist_model = None
        specialist_labels = []

def select_model(expected_label):
    expected = normalize_label(expected_label)

    if (
        expected in SPECIALIST_TARGETS
        and specialist_model is not None
        and len(specialist_labels) > 0
    ):
        return specialist_model, specialist_labels, SPECIALIST_THRESHOLD, "specialist"

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
        "stats": {
            "benar": 0,
            "salah": 0
        },
        "expected_label": "",
        "start_time": None
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
            "stats": {
                "benar": 0,
                "salah": 0
            },
            "expected_label": "",
            "start_time": None
        }

    data = data or {}

    expected = data.get("expectedLabel")
    if expected is None:
        expected = data.get("expected_label")
    if expected is None:
        expected = data.get("label")
    if expected is None:
        expected = data.get("nama_latihan")
    if expected is None:
        expected = ""

    normalized_expected = normalize_label(expected)

    sessions[sid].update({
        "buffer": [],
        "stats": {
            "benar": 0,
            "salah": 0
        },
        "expected_label": normalized_expected,
        "start_time": time.time()
    })

    print(f"[START] {sid} | target: {normalized_expected}")

    emit("session_started", {
        "expected_label": normalized_expected
    })



@socketio.on("send_pose_data")
def handle_pose_data(data):
    sid = request.sid

    if sid not in sessions:
        return

    session = sessions[sid]

    # 1. Terima paket 30 frame langsung dari Flutter
    sequence_buffer = data.get("landmarks")

    # Validasi Dasar
    if not isinstance(sequence_buffer, list) or len(sequence_buffer) == 0:
        return

    # 2. Cek apakah benar ini 2D Array (List of List)
    if not isinstance(sequence_buffer[0], list):
        print(f"⚠️ Salah format! Flutter harus kirim List<List<double>> | sid={sid}")
        return

    # 3. Cek apakah jumlah frame-nya pas 30 (SEQ_LEN)
    if len(sequence_buffer) != SEQ_LEN:
        return

    expected = session.get("expected_label") or ""
    expected_norm = normalize_label(expected)

    selected_model, selected_labels, threshold, model_name = select_model(expected_norm)

    if selected_model is None or len(selected_labels) == 0:
        print("❌ Model/labels kosong")
        return

    try:
        # 4. SULAP LANGSUNG JADI TENSOR (Tidak perlu pakai buffer Python lagi!)
        input_tensor = np.array([sequence_buffer], dtype=np.float32)
        prediction = selected_model.predict(input_tensor, verbose=0)[0]

        max_idx = int(np.argmax(prediction))
        confidence = float(prediction[max_idx])

        raw_label = selected_labels[max_idx] if max_idx < len(selected_labels) else "unknown"
        predicted_label = normalize_label(raw_label)

        is_match = predicted_label == expected_norm
        is_valid = confidence >= threshold
        is_correct = is_match and is_valid

        print(
            f"🧠 PREDICT BATCH | model={model_name} | "
            f"shape={input_tensor.shape} | "
            f"pred={predicted_label} | "
            f"expected={expected_norm} | "
            f"conf={confidence:.2f} | "
            f"match={is_match}"
        )

        emit("inference_result", {
            "label": predicted_label if is_correct else "Gerakan salah", 
            "confidence": confidence,
            "is_valid": is_valid,
            "is_match": is_match,
            "is_correct": is_correct,
            "feedback": "Gerakan benar" if is_correct else "Gerakan belum sesuai",
        })

    except Exception as e:
        print("❌ [ERROR] inference error:", e)


# ===============================
# END EXERCISE
# ===============================
@socketio.on("end_exercise")
def handle_end_exercise():
    sid = request.sid

    if sid not in sessions:
        return

    session = sessions[sid]
    stats = session["stats"]

    total = stats["benar"] + stats["salah"]
    akurasi = (
    (stats["benar"] / total) * 100
    if total > 0
    else 0.0
)

    durasi_latihan = 0.0
    if session.get("start_time") is not None:
        durasi_latihan = time.time() - session["start_time"]

    emit("exercise_summary", {
        "total_benar": stats["benar"],
        "total_salah": stats["salah"],
        "akurasi": akurasi,
        "durasi_latihan": durasi_latihan
    })

    print(
        f"📊 [SUMMARY] sid={sid} | "
        f"benar={stats['benar']} | "
        f"salah={stats['salah']} | "
        f"akurasi={akurasi:.2f} | "
        f"durasi={durasi_latihan:.2f}s"
    )

    session.update({
        "buffer": [],
        "stats": {
            "benar": 0,
            "salah": 0
        },
        "expected_label": "",
        "start_time": None
    })
