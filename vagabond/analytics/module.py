
from vagabond.services import dbmanager
from flask import request
import hashlib
import logging

log = logging.getLogger(__name__)

# mainly for security and analytics
def associate_fingerprint_to_session(fingerprint: str, sessionID: str) -> None:
    log.warning("associating fingerprint to session id")
    dbmanager.write(query_str="""
        UPDATE sessions_table
        SET fingerprint_id = %s
        WHERE sid = %s
    """, params=(fingerprint, sessionID,))

def create_fingerprint() -> str:
    user_agent = request.headers.get("User-Agent")
    accepted_languages = request.headers.get("Accept-Language")
    ip_address = request.remote_addr

    combined_fingerprint = ip_address + user_agent + accepted_languages

    hashobj = hashlib.sha256()
    hashobj.update(combined_fingerprint.encode('utf-8'))

    return hashobj.hexdigest()

