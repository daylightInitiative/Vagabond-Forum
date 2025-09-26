
import logging

from vagabond.queries import *
from vagabond.constants import *
from vagabond.sessions.module import (
    create_session, invalidate_session,
    get_userid_from_session, is_user_logged_in,
    get_session_id, redirect_if_already_logged_in,
    abort_if_not_signed_in, get_tdid
)
from vagabond.utility import rows_to_dict, deep_get, get_censored_email
from vagabond.utility import included_reload_files
from vagabond.forum.module import is_admin
from vagabond.signup import signup
from vagabond.logFormat import setup_logger # we love colors
from vagabond.avatar import create_user_avatar, update_user_avatar

from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory, abort, make_response
from dotenv import load_dotenv
from random import randint

#blueprints
from vagabond.sessions import session_bp
from vagabond.login import login_bp
from vagabond.forum import forum_bp
from vagabond.signup import signup_bp

#services
from vagabond.dbmanager import DBManager, DBStatus
from vagabond.services import init_extensions, dbmanager, app_config, moment, limiter


load_dotenv()

app = Flask(__name__)

app.config["custom_config"] = app_config
log = logging.getLogger() # root logger doesnt need an identifier
setup_logger(log)

# init all extensions
init_extensions(app)

# register all blueprints
app.register_blueprint(session_bp)
app.register_blueprint(login_bp)
app.register_blueprint(forum_bp)
app.register_blueprint(signup_bp)

# great tutorial on the usage of templates
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ii-templates

# learned that context processors exist ! no more spaghetti arg passing to render template
# I will eventually switch over to blueprints as the site gains complexity
@app.context_processor
def inject_jinja_variables():
    sid = get_session_id()
    user_id = get_userid_from_session(sessionID=sid)
    log.debug(f"yay!")
    return {
        "is_authenticated": is_user_logged_in(),
        "is_superuser": is_admin(user_id)
    }

@app.before_request
def log_request_info():
    if '/static' in request.path: # we dont want resources to count as a website visit
        return
    log.info(f"[ACCESS] {request.method} {request.path} from {request.remote_addr}")
    dbmanager.write(query_str='UPDATE webstats SET hits = hits + 1;')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error_pages/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    log.critical("Internal Server Error has occured: %s", error)
    return render_template('error_pages/500.html'), 500

@app.route("/news.html")
def news():

    # returns an array of tuples, index one out
    raw_rows, column_names = dbmanager.read(query_str=QUERY_NEWS_POSTS, get_columns=True, fetch=True)
    news_feed = rows_to_dict(raw_rows, column_names)

    return render_template("news.html", news_feed=news_feed or [])

@app.route("/reading_list.html")
def reading_list():
    return render_template("reading.html")



@app.route("/")
def index():
    random_number = randint(1, 99999)
    get_hits = dbmanager.read(query_str="SELECT hits FROM webstats;")

    num_hits = deep_get(get_hits, 0, 0)

    forum_cat_rows, forum_cat_cols = dbmanager.read(query_str=QUERY_FORUM_CATEGORIES, get_columns=True)
    categories_list = rows_to_dict(forum_cat_rows, forum_cat_cols)

    log.debug(categories_list)

    return render_template("index.html", number=random_number, num_hits=num_hits, forum_categories=categories_list or {})


@app.route('/profile', methods=["GET", "POST"])
def profile():

    seshid = get_session_id()
    log.debug(is_user_logged_in())
    if not is_user_logged_in():
        abort(401)

    userid = get_userid_from_session(sessionID=seshid)
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

    sessions = []
    for i in range(len(get_list)):
        sessions.append(dict(
            active = deep_get(get_list, i, 0),
            lastLogin = deep_get(get_list, i, 1),
            userAgent = deep_get(get_list, i, 2),
            ipaddr = deep_get(get_list, i, 3)
        ))

    return render_template("profile.html", userinfo=userinfo, sessions=sessions)


# here we go....





@app.route('/static/<path:filename>')
@limiter.exempt
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, extra_files=included_reload_files)