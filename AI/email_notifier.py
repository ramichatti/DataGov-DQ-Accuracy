"""Secure email notifier using Gmail SMTP.

Credentials are read from environment variables (or a local .env file),
never hard-coded. Required variables:
    SMTP_SENDER      (e.g. ramichatti14@gmail.com)
    SMTP_APP_PASSWORD (Gmail app password)
    SMTP_RECEIVER    (e.g. chattir764@gmail.com)
    SMTP_SERVER      (default smtp.gmail.com)
    SMTP_PORT        (default 587)
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads project .env file if present
except Exception:
    pass


def get_smtp_config():
    """Return SMTP config from environment variables."""
    config = {
        "sender": os.environ.get("SMTP_SENDER", "").strip(),
        "app_password": os.environ.get("SMTP_APP_PASSWORD", "").strip(),
        "receiver": os.environ.get("SMTP_RECEIVER", "").strip(),
        "server": os.environ.get("SMTP_SERVER", "smtp.gmail.com").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587").strip() or 587),
    }
    return config


def is_email_configured():
    cfg = get_smtp_config()
    return bool(cfg["sender"] and cfg["app_password"] and cfg["receiver"])


def send_email(subject, body_text, body_html=None):
    """Send an email. Raises if SMTP fails."""
    cfg = get_smtp_config()
    if not is_email_configured():
        raise RuntimeError(
            "SMTP non configuré : définissez SMTP_SENDER, SMTP_APP_PASSWORD "
            "et SMTP_RECEIVER dans les variables d'environnement ou .env"
        )

    msg = MIMEMultipart("alternative")
    msg["From"] = cfg["sender"]
    msg["To"] = cfg["receiver"]
    msg["Subject"] = subject

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    logger.info(f"Envoi de l'email à {cfg['receiver']} via {cfg['server']}:{cfg['port']}...")
    with smtplib.SMTP(cfg["server"], cfg["port"], timeout=60) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(cfg["sender"], cfg["app_password"])
        server.sendmail(cfg["sender"], [cfg["receiver"]], msg.as_string())
    logger.info("Email envoyé avec succès.")
    return True
