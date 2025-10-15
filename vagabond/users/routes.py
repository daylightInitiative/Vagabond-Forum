from vagabond.constants import RouteStatus
from vagabond.users import users_bp
from vagabond.services import dbmanager as db, limiter

from vagabond.utility import deep_get, rows_to_dict
from flask import jsonify, url_for
from vagabond.flask_wrapper import custom_render_template
import logging

# the idea is that each user has their own profile
log = logging.getLogger(__name__)

# we're going to do a SO type URL here https://stackoverflow.com/users/1234567890/john-doe
@users_bp.route("/users/<int:userid>/")
def serve_userpage(userid):

    if not userid:
        return jsonify({"error": RouteStatus.INVALID_USER_ID.value}), 422
    
    user_rows, user_cols = db.read(query_str="""
        SELECT p.description, users.id, username, is_online, lastSeen, join_date, avatar_hash
        FROM users
        LEFT JOIN profiles AS p ON p.profile_id = users.id
        WHERE users.id = %s
    """, params=(userid,), get_columns=True)

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

    return custom_render_template("user_page.html", userinfo=user_info, posts=get_user_posts)