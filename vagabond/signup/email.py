from itsdangerous import URLSafeTimedSerializer
from flask import current_app, url_for, abort
import smtplib
from smtplib import SMTPException, SMTPConnectError, SMTPRecipientsRefused, SMTPSenderRefused, SMTPDataError
from typing import TypedDict, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, find_dotenv
from vagabond.services import app_config
import logging
import os
load_dotenv(find_dotenv("secrets.env"))

log = logging.getLogger(__name__)


class EmailContent(TypedDict):
    subject: str
    body: str
    attachments: List[str] # or List[Path] cant decide yet

def send_email(receiver_email: str, email_dict: EmailContent) -> None:
    email_config = app_config.smtp_config
    smtp_host = email_config.get("host")
    smtp_port = email_config.get("port")
    src_email = email_config.get("public_email")

    message = MIMEMultipart()
    message["From"] = src_email
    message["To"] = receiver_email
    message["Subject"] = email_dict.get("subject")
    message.attach(MIMEText(email_dict.get("body"), "html"))

    try:
        with smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=10) as server:
            # attach other attachments....
            #server.login(sender_email, password)
            #server.starttls() may be required by some real servers (but mailpit is unencrypted)
            server.send_message(msg=message, from_addr=src_email, to_addrs=receiver_email)
            log.debug(f"Email sent to {receiver_email}")

    except (SMTPConnectError, SMTPRecipientsRefused, SMTPSenderRefused, SMTPDataError) as smtp_err:
        log.error(f"SMTP error occurred while sending email: {smtp_err}")

    except SMTPException as e:
        log.error(f"A SMTP error occurred: {e}")

    except Exception as e:
        log.error(f"Unexpected error occurred while sending email: {e}")

    return None

def send_confirmation_code(email: str, code: str) -> None:
    confirmation_url = url_for("signup.confirm_signup_code", token=code, _external=True)
    send_email(receiver_email=email, email_dict={
        "subject": "Your temporary signup code",
        "body": f"""
            <b>Hello, user use this temporary link to complete your account setup.</b><br><br>
            <a href="{confirmation_url}">Click this link<a> to finalize your account setup: 
        """
    })
    return None

def generate_token(email):
    serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
    return serializer.dumps(email, salt=os.getenv("SECURITY_PASSWORD_SALT"))

def confirm_token(token, expiration=3600) -> str | bool:
    serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
    try:
        email = serializer.loads(
            token, salt=os.getenv("SECURITY_PASSWORD_SALT"), max_age=expiration
        )
        return email
    except Exception:
        return False