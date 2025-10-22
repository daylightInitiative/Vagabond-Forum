from vagabond.constants import ResponseMessage, RouteStatus
from flask import Response, jsonify, render_template
import logging

from vagabond.services import dbmanager as db
log = logging.getLogger(__name__)

def success_response(status: ResponseMessage, http_code: int = 200) -> tuple[Response, int]:
    payload = {
        "success": status.value
    }

    return jsonify(payload), http_code

def error_response(status: RouteStatus, http_code: int = 400, extra_info: dict = None) -> tuple[Response, int]:
    payload = {
        "error": status.value
    }

    if extra_info:
        payload.update(extra_info)

    return jsonify(payload), http_code

def custom_render_template(template_name: str, **context):

    from vagabond.sessions.module import get_fingerprint

    user_fingerprint = get_fingerprint() # add this to the inject context processor
    db.write(query_str="""
        INSERT INTO impressions (impression_hash, impression_hits, impression_first_visited)
        VALUES (%s, 1, NOW())
        ON CONFLICT (impression_hash)
        DO UPDATE SET impression_hits = impressions.impression_hits + 1
    """, params=(user_fingerprint,))

    raw_template_name = template_name.split(".")[0]
    log.debug(raw_template_name)

    db.write(query_str="""
        INSERT INTO impression_durations (impression_hash, impression_start, impression_page)
        VALUES (%s, NOW(), %s)
    """, params=(user_fingerprint, raw_template_name))
    return render_template(template_name, **context)