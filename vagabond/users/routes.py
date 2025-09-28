from vagabond.users import users_bp
from vagabond.services import dbmanager, limiter

from vagabond.utility import deep_get, rows_to_dict
from flask import render_template, url_for
import logging

# the idea is that each user has their own profile
log = logging.getLogger(__name__)

# we're going to do a SO type URL here https://stackoverflow.com/users/1234567890/john-doe
@users_bp.route("/users/<int:userid>/")
def serve_userpage(userid):

    if not userid:
        return '', 422
    
    # based on that userid lets do a query to get user information
    user_rows, user_cols = dbmanager.read(query_str="""
        SELECT p.description, username, is_online, lastSeen, join_date, avatar_hash
        FROM users
        LEFT JOIN profiles AS p ON p.profile_id = users.id
        WHERE users.id = %s
    """, params=(userid,), get_columns=True)

    user_dict = rows_to_dict(user_rows, user_cols)
    user_info = deep_get(user_dict, 0)

    log.debug(user_info)

    return render_template("user_page.html", userinfo=user_info)