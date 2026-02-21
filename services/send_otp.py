# app/services/email_service.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_verification_email(to: str, code: str):
    sender_email = os.getenv("SMTP_EMAIL")
    sender_pass = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = to
    msg["Subject"] = "Kode Verifikasi Akun"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; text-align: center;">
        <h2>Verifikasi Akun</h2>
        <p>Kode verifikasi Anda adalah:</p>
        <h1 style="letter-spacing:5px; color: #2c3e50;">{code}</h1>
        <p>Kode ini berlaku untuk waktu terbatas. Jangan bagikan kepada siapa pun.</p>
    </div>
    """

    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_pass)
        server.send_message(msg)
