from vagabond.constants import RouteError
from vagabond.flask_wrapper import custom_render_template
from flask import request, redirect, abort, jsonify

from vagabond.moderation import is_admin, requires_permission
from vagabond.moderation import UserPermission as Perms
from vagabond.sessions.module import abort_if_not_signed_in, get_session_id, get_userid_from_session, is_valid_session
from vagabond.admin import admin_bp
from vagabond.services import dbmanager, limiter
import logging

log = logging.getLogger(__name__)

def contains_json_key_or_error(dictionary: dict, keydict: dict) -> None:
    for key, value in keydict.items():
        key_exists = dictionary.get(key)
        if not key_exists or not type(key_exists) == value:
            return jsonify({"error": RouteError.INVALID_FORM_DATA}), 422
    return None

@admin_bp.route("/moderation/ticket", methods=['POST'])
def create_ticket():
    ticket_data = request.get_json()
    log.info("Received a new ticket from user support")
    contains_json_key_or_error(dictionary=ticket_data, keydict={
        "ticket_type": str,
        "title": str,
        "contents": str
    })

    sid = get_session_id()
    if not sid or not is_valid_session(sessionID=sid):
        abort(401)

    userid = get_userid_from_session(sessionID=sid)

    dbmanager.write(query_str="""
        INSERT INTO tickets (ticket_type, ticket_status, title, contents, reporter_userid)
            VALUES (%s, %s, %s, %s, %s)
    """, params=(ticket_data.get("ticket_type"), "needs_investigation", ticket_data.get("title"), ticket_data.get("contents"), userid,))


    return '', 200

@admin_bp.route("/admin", methods=['GET', 'POST'])
@requires_permission([Perms.ADMIN, Perms.MODERATOR])
def serve_admin_panel():
    
    abort_if_not_signed_in()

    sid = get_session_id()
    user_id = get_userid_from_session(sessionID=sid)

    if not is_admin(userid=user_id):
        abort(401)

    user_to_moderate = request.args.get("userid")
    log.debug(user_to_moderate)

    return custom_render_template("admin_panel.html")