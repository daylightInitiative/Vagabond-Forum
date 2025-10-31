from vagabond.constants import RouteError, SuccessMessage
from vagabond.moderation import manage_user_mute
from vagabond.sessions.module import get_session_id, get_userid_from_session
from vagabond.users import users_bp
from vagabond.services import dbmanager as db, limiter

from vagabond.utility import deep_get, get_userid_from_email, rows_to_dict
from flask import jsonify, request, url_for
from vagabond.flask_wrapper import custom_render_template, error_response, success_response
import logging

# the idea is that each user has their own profile
log = logging.getLogger(__name__)

# we're going to do a SO type URL here https://stackoverflow.com/users/1234567890/john-doe
@users_bp.route("/users/<int:userid>/", methods=["GET", "POST"])
def serve_userpage(userid):

    if request.method == "GET":
            
        if not userid:
            return error_response(RouteError.INVALID_USER_ID, 422)
        
        sid = get_session_id()
        
        if not sid:
            user_rows, user_cols = db.read(query_str="""
                SELECT p.description, users.id, username, is_online, lastSeen, join_date, avatar_hash
                FROM users
                LEFT JOIN profiles AS p ON p.profile_id = users.id
                WHERE users.id = %s
            """, params=(userid,), get_columns=True)
        else:
            current_userid = get_userid_from_session(sessionID=sid)

            user_rows, user_cols = db.read(query_str="""
                SELECT p.description, users.id, username, is_online, lastSeen, join_date, avatar_hash,
                    CASE 
                        WHEN muted_users_table.userid IS NOT NULL THEN TRUE 
                        ELSE FALSE 
                    END AS is_muted
                FROM users
                LEFT JOIN profiles AS p ON p.profile_id = users.id
                LEFT JOIN muted_users_table ON muted_users_table.userid = users.id AND muted_users_table.muterid = %s
                WHERE users.id = %s
            """, params=(current_userid, userid,), get_columns=True)

        user_dict = rows_to_dict(user_rows, user_cols)
        user_info = deep_get(user_dict, 0)

        post_rows, post_cols = db.read(query_str="""
            SELECT id, category_id, title, views
            FROM posts
            WHERE author = %s
            ORDER BY creation_date DESC
            LIMIT 6 OFFSET 1
        """, get_columns=True, params=(userid,))

        get_user_posts = rows_to_dict(post_rows, post_cols)

        log.debug(user_info)

        return custom_render_template("user_page.html", userinfo=user_info, posts=get_user_posts)
    elif request.method == "POST":

        data = request.get_json()
        sid = get_session_id()

        # must be logged in to use the api, eventually all this moderation stuff will be centralized to one blueprint
        if not sid:
            return error_response(RouteError.INVALID_SESSION, 401)
        
        current_userid = get_userid_from_session(sessionID=sid)
        
        modaction = data.get("action")
        userToMute = data.get("userid")

        log.debug("%s,%s", modaction, userToMute)

        if not modaction or not userToMute or userToMute == current_userid:
            return error_response(RouteError.INVALID_FORM_DATA, 422)

        if modaction == "mute":
            manage_user_mute(userToMuteID=userToMute, muterID=current_userid, is_muted=True)
        elif modaction == "unmute":
            manage_user_mute(userToMuteID=userToMute, muterID=current_userid, is_muted=False)

        return success_response(SuccessMessage.COMPLETED_MODACTION, 200)

