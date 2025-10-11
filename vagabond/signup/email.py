from itsdangerous import URLSafeTimedSerializer
from flask import current_app, url_for, abort
import smtplib
from smtplib import SMTPException, SMTPConnectError, SMTPRecipientsRefused, SMTPSenderRefused, SMTPDataError
from typing import TypedDict, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, find_dotenv
from vagabond.services import app_config, dbmanager
from vagabond.utility import deep_get
from vagabond.sessions.module import get_tsid
import logging
import os
import string
import secrets
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

"""Generates the 2fa code, adds it to the db and then returns"""
def generate_2FA_code(sessionID: str) -> str:
    new_2fa_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
    tsid = get_tsid(sessionID=sessionID)

    # only one code, on conflict update the code
    dbmanager.write(query_str="""
        INSERT INTO verification_codes (temp_session_id, code)
        VALUES (%s, %s)
        ON CONFLICT (temp_session_id) DO UPDATE
        SET 
            code = EXCLUDED.code,
            created_at = NOW(),
            expires_at = NOW() + INTERVAL '1 hour';
    """, params=(tsid, new_2fa_code,))

    return new_2fa_code

def confirm_2FA_code(sessionID: str, code: str) -> bool:
    tsid = get_tsid(sessionID=sessionID)

    code_exists = dbmanager.read(query_str="""
        SELECT TRUE
        FROM verification_codes
        WHERE temp_session_id = %s AND expires_at > NOW() AND code = %s
    """, params=(tsid, code,))

    if not code_exists:
        return False

    code_is_valid = deep_get(code_exists, 0, 0)

    if not code_is_valid:
        return False
    
    return True

def send_2fa_code(email: str, code: str) -> None:
    send_email(receiver_email=email, email_dict={
        "subject": "Your 2fa authentication code",
        "body": f"""
            <b>Hello user, use this temporary code to enable 2fa.</b><br><br>
            <p>{code}</p>
        """
    })
    return None

def send_confirmation_code(email: str, code: str) -> None:
    confirmation_url = url_for("signup.confirm_signup_code", token=code, _external=True)
    send_email(receiver_email=email, email_dict={
        "subject": "Your temporary signup code",
        "body": f"""
            <b>Hello user, use this temporary link to complete your account setup.</b><br><br>
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