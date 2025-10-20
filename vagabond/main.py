
import logging
import os

from vagabond.queries import *
from vagabond.constants import *
from vagabond.sessions.module import (
    get_userid_from_session, is_user_logged_in, get_session_id, get_fingerprint, is_valid_csrf_or_abort, CSRF, is_valid_session, invalidate_session
)
from vagabond.utility import rows_to_dict, deep_get, get_email_from_userid, get_current_TIMESTAMPZ, get_email_subject_date
from vagabond.utility import included_reload_files
from vagabond.moderation import is_admin, hellban_user
from vagabond.email import send_email
from vagabond.logFormat import setup_logger # we love colors

from flask import Flask, jsonify, request, redirect, url_for, send_from_directory, abort, make_response
from random import randint
from dotenv import load_dotenv, find_dotenv
from vagabond.flask_wrapper import custom_render_template
from werkzeug.middleware.proxy_fix import ProxyFix # when using nginx, we need to use this

#blueprints
from vagabond.sessions import session_bp
from vagabond.login import login_bp
from vagabond.forum import forum_bp
from vagabond.signup import signup_bp
from vagabond.profile import profile_bp
from vagabond.users import users_bp
from vagabond.analytics import analytics_bp
from vagabond.admin import admin_bp
from vagabond.messaging import messaging_bp

#services
from vagabond.dbmanager import DBManager, DBStatus
from vagabond.services import init_extensions, dbmanager as db, app_config, moment, limiter
from vagabond.flask_wrapper import custom_render_template

load_dotenv(find_dotenv("secrets.env"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["custom_config"] = app_config

log = logging.getLogger() # root logger doesnt need an identifier
setup_logger(log)

if app_config.flask_config.get("proxy") == True:

    log.warning("[+] Running on proxy, applying wsgi proxy fix")
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

CSRF(app)

# init all extensions
init_extensions(app)

# register all blueprints
app.register_blueprint(session_bp)
app.register_blueprint(login_bp)
app.register_blueprint(forum_bp)
app.register_blueprint(signup_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(users_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(messaging_bp)

# great tutorial on the usage of templates
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ii-templates

# learned that context processors exist ! no more spaghetti arg passing to render template
# I will eventually switch over to blueprints as the site gains complexity
@app.context_processor
def inject_jinja_variables():
    from vagabond.sessions.module import get_csrf_token
    sid = get_session_id()
    user_id = get_userid_from_session(sessionID=sid)
    return {
        "is_authenticated": is_user_logged_in(),
        "current_userid": user_id,
        "is_superuser": is_admin(userid=user_id),
        "get_csrf_token": get_csrf_token
    }



@app.before_request
def log_request_info():
    if '/static' in request.path: # we dont want resources to count as a website visit
        return
    
    sid = get_session_id()
    if not sid:
        return
        
    if not is_valid_session(sessionID=sid):
        invalidate_session(sessionID=sid)
        return

    log.info(f"[ACCESS] {request.method} {request.path} from {request.remote_addr}")
    db.write(query_str='UPDATE webstats SET hits = hits + 1, visited_timestamp = NOW()')

    site_referral = request.headers.get("Referer")
    if site_referral:

        db.write(query_str="""
            INSERT INTO referrer_links (link_origin, hits)
            VALUES (%s, 1)
            ON CONFLICT (link_origin)
            DO UPDATE SET hits = referrer_links.hits + 1
        """, params=(site_referral,))

    # create the fingerprint hash
    user_fingerprint = get_fingerprint()

    # add the fingerprint to the database if it hasnt already
    # record the fingerprint, the number of times they've visited and the first time they visited (first seen the in wild)

    user_id = get_userid_from_session(sessionID=sid)

    if user_id:
        db.write(query_str="""
            UPDATE users
            SET lastSeen = NOW(), is_online = TRUE
            WHERE id = %s
        """, params=(user_id,))

@app.errorhandler(401)
def not_authorized_error(error):
    return custom_render_template('error_pages/401.html'), 401

@app.errorhandler(404)
def not_found_error(error):
    return custom_render_template('error_pages/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    log.critical("Internal Server Error has occured: %s", error)

    timestamp_now = get_current_TIMESTAMPZ()
    subject_datestamp = get_email_subject_date()

    # send a ping to sysadmins/site admins
    sys_email = get_email_from_userid(userid=1) # system user
    send_email(receiver_email=sys_email, email_dict={
        "subject": f"Internal Server Error Report, {subject_datestamp}",
        "body": f"""
            Error 500, '{error}'
            This report was automatically generated at {timestamp_now}
        """
    })

    return custom_render_template('error_pages/500.html'), 500

@app.route("/news.html")
def news():

    raw_rows, column_names = db.read(query_str=QUERY_NEWS_POSTS, get_columns=True, fetch=True)
    news_feed = rows_to_dict(raw_rows, column_names)

    return custom_render_template("news.html", news_feed=news_feed or [])

@app.route("/reading_list.html")
def reading_list():
    return custom_render_template("reading.html")

@app.route("/")
def index():
    random_number = randint(1, 99999)
    get_hits = db.read(query_str="SELECT hits FROM webstats;")

    num_hits = deep_get(get_hits, 0, 0)

    sid = get_session_id()
    user_id = get_userid_from_session(sessionID=sid)

    named_params = {
        "current_userid": user_id
    }
    forum_cat_rows, forum_cat_cols = db.read(query_str=QUERY_FORUM_CATEGORIES, get_columns=True, params=named_params)
    categories_list = rows_to_dict(forum_cat_rows, forum_cat_cols)

    #log.debug(categories_list)

    return custom_render_template("index.html", number=random_number, num_hits=num_hits, forum_categories=categories_list or {})


@app.route('/static/<path:filename>')
@limiter.exempt
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':

    host = app_config.flask_config.get("host")
    lport = app_config.flask_config.get("post")

    app.run(debug=True, host=host, port=lport, extra_files=included_reload_files)