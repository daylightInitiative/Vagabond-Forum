from vagabond.flask_wrapper import custom_render_template
from flask import request, redirect, abort

from vagabond.moderation import is_admin
from vagabond.sessions.module import abort_if_not_signed_in, get_session_id, get_userid_from_session
from vagabond.admin import admin_bp
import logging

log = logging.getLogger(__name__)

@admin_bp.route("/admin", methods=['GET', 'POST'])
def serve_admin_panel():
    
    abort_if_not_signed_in()

    sid = get_session_id()
    user_id = get_userid_from_session(sessionID=sid)

    if not is_admin(userid=user_id):
        abort(401)

    user_to_moderate = request.args.get("userid")
    log.debug(user_to_moderate)

    return custom_render_template("admin_panel.html")