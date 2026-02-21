# app/services/id_generator.py
import random

def generate_random_4_digit() -> str:
    return f"{random.randint(0, 9999):04d}"
