from vagabond.sessions.module import (
    get_session_id, is_user_logged_in, get_userid_from_session, abort_if_not_signed_in
)
from vagabond.services import limiter, dbmanager
from vagabond.profile import profile_bp
from vagabond.utility import deep_get, get_censored_email
from vagabond.flask_wrapper import custom_render_template
from flask import request, redirect, jsonify, url_for
import logging

log = logging.getLogger(__name__)

@profile_bp.route('/profile', methods=["GET", "POST"])
def serve_profile():
    abort_if_not_signed_in()
    seshid = get_session_id()

    userid = get_userid_from_session(sessionID=seshid)

    if request.method == "GET":
        
        get_info = dbmanager.read(query_str="""
            SELECT email, username, join_date, avatar_hash
            FROM users
            WHERE id = %s
        """, params=(userid,))

        email = deep_get(get_info, 0, 0)
        hidden_email = get_censored_email(email)

        username = deep_get(get_info, 0, 1)
        joinDate = deep_get(get_info, 0, 2)
        avatar_hash = deep_get(get_info, 0, 3)

        userinfo = dict(
            userid = userid,
            username = username,
            join_date = joinDate,
            avatar_hash = avatar_hash,
            email = hidden_email
        )

        # get the session profiles to be displayed in the profile file (for right now)
        get_list = dbmanager.read(query_str="""
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
        get_about_me = dbmanager.read(query_str="""
            SELECT description
            FROM profiles
            WHERE profile_id = %s
        """, params=(userid,))

        about_me = deep_get(get_about_me, 0, 0)

        return custom_render_template("profile.html", userinfo=userinfo, sessions=sessions, about_me=about_me)

    elif request.method == "POST":
        about_me = request.form.get("description")

        if not about_me:
            return jsonify("Invalid form data", 422)
        
        truncated_str = about_me[:500] # cannot go past 500 if the javascript fails or they are automating

        dbmanager.write(query_str="""
            UPDATE profiles
            SET description = %s
            WHERE profile_id = %s
        """, params=(truncated_str, userid,))

        log.debug("saved about me: %s", truncated_str)

        return redirect(url_for("profile.serve_profile"))

