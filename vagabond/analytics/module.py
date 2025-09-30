
from flask import request
import hashlib



def create_fingerprint() -> str:
    user_agent = request.headers.get("User-Agent")
    accepted_languages = request.headers.get("Accept-Language")
    ip_address = request.remote_addr

    combined_fingerprint = ip_address + user_agent + accepted_languages

    hashobj = hashlib.sha256()
    hashobj.update(combined_fingerprint.encode('utf-8'))

    return hashobj.hexdigest()

