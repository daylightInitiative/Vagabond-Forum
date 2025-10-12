from flask import current_app as app
from vagabond.constants import RouteError
from vagabond.sessions.module import abort_if_not_signed_in, get_session_id, get_userid_from_session, csrf_exempt, is_valid_session, get_csrf_token
from vagabond.sessions import session_bp
from vagabond.services import dbmanager
from flask import abort, jsonify, request
import logging

log = logging.getLogger(__name__)

@session_bp.route("/csrf-token", methods=["GET"])
@csrf_exempt
def get_new_csrf_token():
    sid = get_session_id()
    if sid and is_valid_session(sid):
        return jsonify({"csrf_token": get_csrf_token()})
    abort(403)

@session_bp.route("/invalidate_other_sessions", methods=["POST"])
def sign_out_other_sessions():
    abort_if_not_signed_in()

    current_sid = get_session_id()

    if not current_sid:
        log.critical("Failed to grab sid while trying to invalidate all other sessions")
        return jsonify({"error": RouteError.INTERNAL_SERVER_ERROR}), 500
    
    user_id = get_userid_from_session(sessionID=current_sid)

    # get all other sessions
    # since invalidation is just setting the active to false, we can just omit any already disabled sessions
    dbmanager.write(query_str="""
        UPDATE sessions_table
        SET active = FALSE
        WHERE user_id = %s AND sid != %s AND active = TRUE
    """, params=(user_id, current_sid,))

    log.debug("signed out of sessions")

    return '', 200