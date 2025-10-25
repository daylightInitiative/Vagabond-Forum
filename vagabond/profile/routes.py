from vagabond.constants import SuccessMessage, RouteError
from vagabond.sessions.module import (
    get_session_id, is_user_logged_in, get_userid_from_session, abort_if_not_signed_in
)
from vagabond.services import limiter, dbmanager as db
from vagabond.profile import profile_bp
from vagabond.email import generate_token, confirm_token, send_2fa_code, generate_2FA_code, confirm_2FA_code
from vagabond.utility import deep_get, get_censored_email, get_email_from_userid
from vagabond.flask_wrapper import custom_render_template, error_response, success_response
from flask import request, redirect, jsonify, url_for, abort
from vagabond.moderation import ModerationAction
import logging

log = logging.getLogger(__name__)

@profile_bp.route('/account/settings/2fa', methods=["GET", "POST"]) # TODO: add easy way to send requests, and PATCH, PUT, DELETE
def toggle_2fa():
    abort_if_not_signed_in()

    sid = get_session_id()
    userid = get_userid_from_session(sessionID=sid)

    if not sid or not userid:
        abort(401)

    if request.method == "GET":
        # generate a new verification code and send to the users email
        user_email = get_email_from_userid(userid=userid)
        new_2FA_code = generate_2FA_code(sessionID=sid)

        send_2fa_code(email=user_email, code=new_2FA_code)
        log.warning("sending verification code to email....")

        return success_response(SuccessMessage.SENT_VERIFICATION_CODE )
    elif request.method == "POST":

        data = request.get_json()
        confirm_code = data.get("confirm_code")

        if not confirm_code:
            return error_response(RouteError.BAD_TOKEN, 422)

        is_2fa_enabled = db.read(query_str="""
            SELECT is_2fa_enabled
            FROM users
            WHERE id = %s
        """, params=(userid,))
        should_2fa_be_enabled = deep_get(is_2fa_enabled, 0, 0) # default its usually at
        log.debug("is 2fa enabled: %s, %s", should_2fa_be_enabled, type(should_2fa_be_enabled))
        
        # bools are super iffy, so we're just going to compare using a number
        if not isinstance(should_2fa_be_enabled, bool):
            return error_response(RouteError.INVALID_FORM_DATA, 422)
        
        is_enabled = not should_2fa_be_enabled

        action = ModerationAction.ENABLE_2FA if is_enabled else ModerationAction.DISABLE_2FA

        db.write(query_str="""
            INSERT INTO moderation_actions (action, target_user_id, performed_by, reason, created_at)
                VALUES (%s, %s, %s, %s, NOW())
        """, params=(
            action.value,
            userid,
            1, # "SYSTEM" user
            "User manually authenticated 2FA"
        ))

        if not confirm_2FA_code(sessionID=sid, code=confirm_code):
            return error_response(RouteError.BAD_TOKEN, 422) # somehow display/handle this on the frontend

        db.write(query_str="""
            UPDATE users
            SET is_2fa_enabled = %s
            WHERE id = %s
        """, params=(is_enabled, userid,))

        log.warning("Toggled 2fa, following a successful email verification")

        return redirect(url_for("profile.serve_profile"))


@profile_bp.route('/profile', methods=["GET", "POST"])
def serve_profile():
    abort_if_not_signed_in()
    seshid = get_session_id()

    userid = get_userid_from_session(sessionID=seshid)

    if request.method == "GET":
        
        get_info = db.read(query_str="""
            SELECT email, username, join_date, avatar_hash, is_2fa_enabled
            FROM users
            WHERE id = %s
        """, params=(userid,))

        email = deep_get(get_info, 0, 0)
        hidden_email = get_censored_email(email)

        username = deep_get(get_info, 0, 1)
        joinDate = deep_get(get_info, 0, 2)
        avatar_hash = deep_get(get_info, 0, 3)
        is_2fa_enabled = deep_get(get_info, 0, 4)

        userinfo = dict(
            userid = userid,
            username = username,
            join_date = joinDate,
            avatar_hash = avatar_hash,
            email = hidden_email,
            is_2fa_enabled = is_2fa_enabled
        )

        # get the session profiles to be displayed in the profile file (for right now)
        get_list = db.read(query_str="""
            SELECT active, lastLogin, display_user_agent, ipaddr
            FROM sessions_table
            WHERE user_id = %s
            ORDER BY lastLogin DESC
        """, params=(userid,))

        n_sessions = len(get_list)
        sessions = []
        for i in range(n_sessions):
            sessions.append(dict(
                active = deep_get(get_list, i, 0),
                lastLogin = deep_get(get_list, i, 1),
                userAgent = deep_get(get_list, i, 2),
                ipaddr = deep_get(get_list, i, 3)
            ))

        # if the data exists, we just load it in the about me
        get_about_me = db.read(query_str="""
            SELECT description
            FROM profiles
            WHERE profile_id = %s
        """, params=(userid,))

        about_me = deep_get(get_about_me, 0, 0)

        return custom_render_template("profile.html", userinfo=userinfo, sessions=sessions, about_me=about_me)

    elif request.method == "POST":
        about_me = request.form.get("description")

        if not about_me:
            return error_response(RouteError.INVALID_FORM_DATA, 422)
        
        truncated_str = about_me[:500] # cannot go past 500 if the javascript fails or they are automating

        db.write(query_str="""
            UPDATE profiles
            SET description = %s
            WHERE profile_id = %s
        """, params=(truncated_str, userid,))

        log.debug("saved about me: %s", truncated_str)

        return redirect(url_for("profile.serve_profile"))

