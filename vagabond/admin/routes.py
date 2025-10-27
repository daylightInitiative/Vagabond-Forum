
from vagabond.constants import SuccessMessage, RouteError
from vagabond.flask_wrapper import custom_render_template, error_response, success_response
from flask import render_template, request, redirect, abort, jsonify

from vagabond.moderation import change_role, hellban_user, is_admin, manage_user_ban, requires_permission
from vagabond.moderation import UserRole as Perms
from vagabond.sessions.module import abort_if_not_signed_in, get_session_id, get_userid_from_session, is_valid_session
from vagabond.admin import admin_bp
from vagabond.services import dbmanager as db, limiter
import logging

from vagabond.utility import contains_dict_or_error, get_user_info, get_userid_from_username, get_username_from_userid, is_valid_userid

log = logging.getLogger(__name__)

@admin_bp.route("/moderation/ticket", methods=['POST'])
def create_ticket():
    ticket_data = request.get_json()
    log.info("Received a new ticket from user support")
    contains_dict_or_error(dictionary=ticket_data, keydict={
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

    return success_response(SuccessMessage.CREATED_TICKET )

@admin_bp.route("/admin", methods=['GET', 'POST'])
@requires_permission([Perms.ADMIN, Perms.MODERATOR])
def serve_admin_panel():
    
    abort_if_not_signed_in()

    sid = get_session_id()
    admin_user_id = str(get_userid_from_session(sessionID=sid))

    if not is_admin(userid=admin_user_id):
        abort(401)

    if not is_valid_userid(userID=admin_user_id):
        log.debug("Invalid admin user id, %s", admin_user_id)
        return error_response(RouteError.INVALID_USER_ID, 422)
    
    if request.method == "GET":
        return render_template("admin_panel.html")
    elif request.method == "POST":
        data = request.get_json()
        
        username = data.get("username")
        if not username:
            log.warning("Username %s was not found.", username)
            return error_response(RouteError.INVALID_FORM_DATA, 422)

        target_user_id = get_userid_from_username(username)

        log.debug("checking username %s: %s", username, target_user_id)
 
        if target_user_id is None:
            log.warning("Username %s was not found.", username)
            return error_response(RouteError.INVALID_FORM_DATA, 422)

        modaction = data.get("modaction")
        provided_reason = data.get("reason", None)

        if modaction:
            match modaction:
                case "ban":
                    manage_user_ban(userid=target_user_id, is_banned=True, admin_userid=admin_user_id, reason=provided_reason)
                case "unban":
                    manage_user_ban(userid=target_user_id, is_banned=False, admin_userid=admin_user_id, reason=provided_reason)
                case "shadowban":
                    hellban_user(userid=target_user_id, admin_userid=admin_user_id, reason=provided_reason)
                case "changerole":
                    user_role = data.get("new_user_role")
                    if not user_role:
                        return error_response(RouteError.INVALID_FORM_DATA, 422)

                    change_role(userid=target_user_id, user_role=user_role, admin_userid=admin_user_id)
                case _:
                    user_info = get_user_info(target_user_id)
                    return jsonify(user_info)
        
        return success_response(SuccessMessage.COMPLETED_MODACTION, 200)