# app/services/otp_service.py
import random

def generate_otp() -> str:
    otp = random.randint(1000, 9999)
    return str(otp)
