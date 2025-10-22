from flask import current_app as app, make_response, redirect, url_for
from vagabond.constants import ResponseMessage, RouteStatus
from vagabond.sessions.module import abort_if_not_signed_in, get_session_id, get_userid_from_session, csrf_exempt, is_valid_session, get_csrf_token
from vagabond.sessions import session_bp
from vagabond.services import dbmanager as db
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

# needed to seperate the admission of a cookie to a seperate request, because it interferes with the strict cookie policy
@session_bp.route("/setup_session", methods=["GET"])
@csrf_exempt
def setup_session():
    sid = request.args.get("sid")
    if not sid:
        return error_response(RouteStatus.INVALID_FORM_DATA, 422)
    
    if not is_valid_session(sessionID=sid):
        return error_response(RouteStatus.INVALID_SESSION, 401)

    response = make_response(redirect(url_for("index")))
    response.set_cookie("sessionID", value=sid, max_age=7200, samesite="Strict")

    return response


@session_bp.route("/invalidate_other_sessions", methods=["POST"])
def sign_out_other_sessions():
    abort_if_not_signed_in()

    current_sid = get_session_id()

    if not current_sid:
        log.critical("Failed to grab sid while trying to invalidate all other sessions")
        return error_response(RouteStatus.INTERNAL_SERVER_ERROR, 500)
    
    user_id = get_userid_from_session(sessionID=current_sid)

    # get all other sessions
    # since invalidation is just setting the active to false, we can just omit any already disabled sessions
    db.write(query_str="""
        UPDATE sessions_table
        SET active = FALSE
        WHERE user_id = %s AND sid != %s AND active = TRUE
    """, params=(user_id, current_sid,))

    log.debug("signed out of sessions")

    return success_response(ResponseMessage.SIGNED_OUT_ALL_SESSIONS )