from flask import request
from flask_socketio import emit
from extensions import socketio

import os
import time
import base64
from collections import deque, Counter

import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp


# ======================================================
# CONFIG
# ======================================================

MODEL_PATH = "./lstm/pose_model_lstm.h5"
LABELS_PATH = "./lstm/labels_lstm.txt"

SEQ_LEN = 20
FEATURE_COUNT = 132  # 33 landmark x 4 fitur: x, y, z, visibility

VALID_THRESHOLD = 0.7
STABILITY_WINDOW = 5
MAX_BUFFER_SIZE = 60


# ======================================================
# GLOBAL STATE
# ======================================================

model = None
labels = []
sessions = {}

mp_pose = mp.solutions.pose

pose_detector = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    enable_segmentation=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)


# ======================================================
# FIX LSTM KERAS COMPATIBILITY
# ======================================================

class CustomLSTM(tf.keras.layers.LSTM):
    def __init__(self, *args, **kwargs):
        kwargs.pop("time_major", None)
        super().__init__(*args, **kwargs)


# ======================================================
# HELPER
# ======================================================

def normalize_label(value):
    if value is None:
        return ""

    return str(value).lower().replace("_", " ").strip()


def create_default_session():
    return {
        "buffer": [],
        "prediction_history": deque(maxlen=STABILITY_WINDOW),
        "stats": {
            "benar": 0,
            "salah": 0
        },
        "expected_label": "",
        "start_time": None
    }


def load_pose_model():
    global model, labels

    try:
        print(f"🔧 Loading model: {MODEL_PATH}")

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

        model = tf.keras.models.load_model(
            MODEL_PATH,
            compile=False,
            custom_objects={
                "LSTM": CustomLSTM
            }
        )

        print("✅ Model loaded successfully")

        if not os.path.exists(LABELS_PATH):
            raise FileNotFoundError(f"Labels file not found: {LABELS_PATH}")

        with open(LABELS_PATH, "r", encoding="utf-8") as f:
            labels = [
                line.strip().lower().replace("_", " ")
                for line in f
                if line.strip()
            ]

        if len(labels) == 0:
            raise ValueError("Labels file is empty")

        print(f"✅ Labels loaded: {len(labels)} classes")
        print(f"📌 Sample labels: {labels[:5]}")

    except Exception as e:
        print(f"❌ FATAL LOAD ERROR: {e}")
        model = None
        labels = []


def extract_landmarks_from_base64(image_base64):
    try:
        if not image_base64:
            return None

        # Jika formatnya: data:image/jpeg;base64,/9j/...
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_base64)
        np_arr = np.frombuffer(image_bytes, np.uint8)

        image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if image_bgr is None:
            print("⚠️ [POSE] Gagal decode image dari base64")
            return None

        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        results = pose_detector.process(image_rgb)

        if not results.pose_landmarks:
            return None

        landmarks = []

        for lm in results.pose_landmarks.landmark:
            landmarks.extend([
                float(lm.x),
                float(lm.y),
                float(lm.z),
                float(lm.visibility)
            ])

        if len(landmarks) != FEATURE_COUNT:
            print(
                f"⚠️ [POSE] Landmark length salah: {len(landmarks)}, "
                f"expected: {FEATURE_COUNT}"
            )
            return None

        return landmarks

    except Exception as e:
        print(f"❌ [POSE] extract_landmarks_from_base64 error: {e}")
        return None


def predict_from_buffer(session):
    buffer = session["buffer"]

    indices = np.linspace(0, len(buffer) - 1, SEQ_LEN).astype(int)
    sampled_buffer = [buffer[i] for i in indices]

    input_tensor = np.array([sampled_buffer], dtype=np.float32)

    prediction = model.predict(input_tensor, verbose=0)

    max_idx = int(np.argmax(prediction[0]))
    confidence = float(prediction[0][max_idx])

    raw_label = labels[max_idx] if max_idx < len(labels) else "unknown"
    clean_label = normalize_label(raw_label)

    session["prediction_history"].append(clean_label)

    stable_label = Counter(
        session["prediction_history"]
    ).most_common(1)[0][0]

    expected = normalize_label(session.get("expected_label"))

    is_match = stable_label == expected
    is_valid = confidence >= VALID_THRESHOLD
    is_correct = is_match and is_valid

    if is_correct:
        session["stats"]["benar"] += 1
        feedback = "Gerakan benar"
    else:
        session["stats"]["salah"] += 1

        if not is_valid:
            feedback = "Gerakan belum yakin terdeteksi"
        elif not is_match:
            feedback = "Gerakan belum sesuai"
        else:
            feedback = "Gerakan salah"

    return {
        "label": stable_label,
        "confidence": confidence,
        "is_valid": is_valid,
        "is_match": is_match,
        "is_correct": is_correct,
        "feedback": feedback,
        "total_benar": session["stats"]["benar"],
        "total_salah": session["stats"]["salah"],
        "expected_label": expected
    }


# Load model saat file controller di-import
load_pose_model()


# ======================================================
# SOCKET EVENTS
# ======================================================

@socketio.on("connect")
def handle_connect():
    sid = request.sid

    sessions[sid] = create_default_session()

    print(f"✅ [CONNECT] Client connected: {sid}")

    emit("server_status", {
        "status": "ready",
        "type": "image_base64_mediapipe_lstm",
        "seq_len": SEQ_LEN,
        "feature_count": FEATURE_COUNT
    })


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid

    sessions.pop(sid, None)

    print(f"⚠️ [DISCONNECT] Client disconnected: {sid}")


@socketio.on("start_session")
def handle_start_session(data):
    sid = request.sid

    if sid not in sessions:
        sessions[sid] = create_default_session()

    data = data or {}

    expected = (
        data.get("expected_label")
        or data.get("label")
        or data.get("nama_latihan")
        or ""
    )

    normalized_expected = normalize_label(expected)

    sessions[sid].update({
        "buffer": [],
        "prediction_history": deque(maxlen=STABILITY_WINDOW),
        "stats": {
            "benar": 0,
            "salah": 0
        },
        "expected_label": normalized_expected,
        "start_time": time.time()
    })

    print(f"▶️ [START SESSION] sid: {sid} | target: {normalized_expected}")

    emit("session_started", {
        "status": "started",
        "expected_label": normalized_expected
    })


@socketio.on("send_frame")
def handle_frame(data):
    sid = request.sid

    if sid not in sessions:
        sessions[sid] = create_default_session()

    if model is None:
        emit("inference_result", {
            "label": "model error",
            "confidence": 0.0,
            "is_valid": False,
            "is_match": False,
            "is_correct": False,
            "feedback": "Model belum berhasil dimuat",
            "total_benar": 0,
            "total_salah": 0
        })
        return

    if len(labels) == 0:
        emit("inference_result", {
            "label": "labels error",
            "confidence": 0.0,
            "is_valid": False,
            "is_match": False,
            "is_correct": False,
            "feedback": "Labels belum berhasil dimuat",
            "total_benar": 0,
            "total_salah": 0
        })
        return

    data = data or {}
    image_base64 = data.get("image")

    if not image_base64:
        print(f"⚠️ [WARNING] image kosong dari sid: {sid}")
        return

    session = sessions[sid]

    landmarks = extract_landmarks_from_base64(image_base64)

    if landmarks is None:
        emit("inference_result", {
            "label": "pose tidak terdeteksi",
            "confidence": 0.0,
            "is_valid": False,
            "is_match": False,
            "is_correct": False,
            "feedback": "Pose tidak terdeteksi",
            "total_benar": session["stats"]["benar"],
            "total_salah": session["stats"]["salah"]
        })
        return

    buffer = session["buffer"]
    buffer.append(landmarks)

    if len(buffer) > MAX_BUFFER_SIZE:
        buffer.pop(0)

    if len(buffer) < SEQ_LEN:
        emit("inference_result", {
            "label": "buffering",
            "confidence": 0.0,
            "is_valid": False,
            "is_match": False,
            "is_correct": False,
            "feedback": f"Mengumpulkan frame {len(buffer)}/{SEQ_LEN}",
            "total_benar": session["stats"]["benar"],
            "total_salah": session["stats"]["salah"]
        })
        return

    try:
        result = predict_from_buffer(session)

        print(
            f"ℹ️ [FRAME INFERENCE] sid: {sid} | "
            f"buffer: {len(buffer)} | "
            f"pred: {result['label']} | "
            f"expected: {result['expected_label']} | "
            f"conf: {result['confidence']:.2f} | "
            f"match: {result['is_match']} | "
            f"correct: {result['is_correct']}"
        )

        emit("inference_result", {
            "label": result["label"],
            "confidence": result["confidence"],
            "is_valid": result["is_valid"],
            "is_match": result["is_match"],
            "is_correct": result["is_correct"],
            "feedback": result["feedback"],
            "total_benar": result["total_benar"],
            "total_salah": result["total_salah"]
        })

    except Exception as e:
        print(f"❌ [ERROR] frame inference error: {e}")

        emit("inference_result", {
            "label": "error",
            "confidence": 0.0,
            "is_valid": False,
            "is_match": False,
            "is_correct": False,
            "feedback": "Terjadi error saat inference",
            "total_benar": session["stats"]["benar"],
            "total_salah": session["stats"]["salah"]
        })


# Optional: event lama tetap disediakan supaya tidak langsung error
# kalau Flutter masih sempat mengirim send_pose_data.
@socketio.on("send_pose_data")
def handle_pose_data_deprecated(data):
    sid = request.sid

    print(
        f"⚠️ [DEPRECATED] sid {sid} masih mengirim send_pose_data. "
        f"Gunakan send_frame untuk mode gambar."
    )

    emit("inference_result", {
        "label": "deprecated",
        "confidence": 0.0,
        "is_valid": False,
        "is_match": False,
        "is_correct": False,
        "feedback": "Gunakan send_frame, bukan send_pose_data",
        "total_benar": 0,
        "total_salah": 0
    })


@socketio.on("end_exercise")
def handle_end_exercise():
    sid = request.sid

    if sid not in sessions:
        emit("exercise_summary", {
            "total_benar": 0,
            "total_salah": 0,
            "akurasi": 0.0,
            "durasi_latihan": 0.0
        })
        return

    session = sessions[sid]
    stats = session["stats"]

    total = stats["benar"] + stats["salah"]
    akurasi = stats["benar"] / total if total > 0 else 0.0

    start_time = session.get("start_time")
    durasi_latihan = time.time() - start_time if start_time else 0.0

    emit("exercise_summary", {
        "total_benar": stats["benar"],
        "total_salah": stats["salah"],
        "akurasi": akurasi,
        "durasi_latihan": durasi_latihan
    })

    print(
        f"📊 [SUMMARY] sid: {sid} | "
        f"benar: {stats['benar']} | "
        f"salah: {stats['salah']} | "
        f"akurasi: {akurasi:.2f} | "
        f"durasi: {durasi_latihan:.2f}s"
    )

    session.update({
        "buffer": [],
        "prediction_history": deque(maxlen=STABILITY_WINDOW),
        "stats": {
            "benar": 0,
            "salah": 0
        },
        "start_time": None
    })