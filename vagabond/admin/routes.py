from vagabond.constants import ResponseMessage, RouteStatus
from vagabond.flask_wrapper import custom_render_template, error_response, success_response
from flask import request, redirect, abort, jsonify

from vagabond.moderation import is_admin, requires_permission
from vagabond.moderation import UserPermission as Perms
from vagabond.sessions.module import abort_if_not_signed_in, get_session_id, get_userid_from_session, is_valid_session
from vagabond.admin import admin_bp
from vagabond.services import dbmanager as db, limiter
import logging

from vagabond.utility import contains_json_key_or_error, is_valid_userid

log = logging.getLogger(__name__)

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

    db.write(query_str="""
        INSERT INTO tickets (ticket_type, ticket_status, title, contents, reporter_userid)
            VALUES (%s, %s, %s, %s, %s)
    """, params=(ticket_data.get("ticket_type"), "needs_investigation", ticket_data.get("title"), ticket_data.get("contents"), userid,))

    return success_response(ResponseMessage.CREATED_TICKET )

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

    if not is_valid_userid(userID=user_to_moderate):
        return error_response(RouteStatus.INVALID_USER_ID, 422)
    


    return custom_render_template("admin_panel.html")