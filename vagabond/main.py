
import os
import logging
import traceback
import json
import string

from vagabond.queries import *
from vagabond.session import create_session, is_valid_session, invalidate_session, get_userid_from_session
from vagabond.config import Config
from vagabond.utility import DBManager, rows_to_dict, deep_get, is_valid_email_address, get_userid_from_email, title_to_content_hint
from vagabond.utility import DB_SUCCESS, DB_FAILURE, EXECUTED_NO_FETCH
from vagabond.signup import signup
from vagabond.login import is_valid_login
from vagabond.logFormatter import CustomFormatter # we love colors

from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory, session, abort, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from random import randint

PAGE_LIMIT = 10
load_dotenv()

app = Flask(__name__)
config_path = os.getenv("CONFIG_PATH", "")
if not config_path:
    logging.critical("USAGE: CONFIG_PATH=/path/to/config.json")
    quit(1)

with open(config_path, "r") as f:
    config_data = json.load(f)

app_config = Config(app, config_data)
app.config["custom_config"] = app_config

# Create a logger
log = logging.getLogger(__name__)
log.setLevel(app_config.console_log_level)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(CustomFormatter())

file_handler = logging.FileHandler("app.log")
file_handler.setLevel(app_config.file_log_level)
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
)
file_handler.setFormatter(file_formatter)

log.addHandler(console_handler)
log.addHandler(file_handler)

# create the our db manager
dbmanager = DBManager(app_config)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["400 per hour"],
    storage_options={"socket_timeout": 5},
    storage_uri="memory://localhost:11211",
)

# I use this a lot per route, making it a function so there are no typos
# and I can easily change this key to something else, hopefully more DRY
def get_session_id():
    return request.cookies.get("sessionID")

def is_user_logged_in():
    sid = get_session_id()
    return True if sid and is_valid_session(db=dbmanager, sessionID=sid) else False

def is_admin(userid) -> bool:
    get_is_superuser = dbmanager.read(query_str="""
        SELECT id, is_superuser
        FROM users
        WHERE id = %s
    """, fetch=True, params=(userid,))
    return deep_get(get_is_superuser, 0, 1) or False



# going to add more high level stuff here, like is_superuser()
def abort_if_not_signed_in():
    if not is_user_logged_in():
        abort(401)
    

def redirect_if_already_logged_in():
    if is_user_logged_in():
        return redirect( url_for("index") )

# great tutorial on the usage of templates
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ii-templates

# learned that context processors exist ! no more spaghetti arg passing to render template
# I will eventually switch over to blueprints as the site gains complexity
@app.context_processor
def inject_jinja_variables():
    user_id = get_userid_from_session(db=dbmanager, sessionID=get_session_id())
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
    raw_rows, column_names = dbmanager.read(query_str=QUERY_NEWS_POSTS, fetch=True)
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

    return render_template("index.html", number=random_number, num_hits=num_hits)

# returns temporary data id linked to a session.
def get_tdid(sessionID: str) -> str|None:
    get_tdid = dbmanager.read(query_str="""
        SELECT temp_data_sid
        FROM sessions_table
        WHERE sid = %s
    """, params=(sessionID,))

    if get_tdid == DB_FAILURE:
        log.critical("Failure to fetch TDID")
        return '', 500

    tdid = deep_get(get_tdid, 0, 0)
    return tdid if tdid else None

@app.route("/save_draft", methods=["POST", "GET"])
@limiter.limit("50 per minute", methods=["POST"])
@limiter.limit("50 per minute", methods=["GET"])
def save_draft():
    
    if not is_user_logged_in():
        abort(401)

    if request.method == "GET":
        # get saved draft logic here
        sid = get_session_id()
        temp_session_id = get_tdid(sessionID=sid)
        
        get_draft = dbmanager.read(query_str="""
            SELECT draft_text
            FROM temp_session_data
            WHERE tempid = %s and LENGTH(draft_text) > 0
        """, params=(temp_session_id,))

        saved_draft_text = deep_get(get_draft, 0, 0)

        if not saved_draft_text:
            return '', 204 # no content
        
        draft = {
            "contents": saved_draft_text
        }

        return jsonify(draft), 200



    elif request.method == "POST":
        data = request.get_json()
        log.debug(data)

        # get the current session
        sid = get_session_id()
        # get the temporary data id
        tdid = get_tdid(sessionID=sid)

        text_to_save = data.get("contents")
        save_draft = dbmanager.write(query_str="""
            UPDATE temp_session_data
            SET draft_text = %s
            WHERE tempid = %s
        """, params=(text_to_save, tdid,))

        if save_draft == DB_FAILURE:
            log.critical("Failed to save draft data for tdid: %s", tdid)
            return '', 500

    return '', 200

    

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("70 per minute", methods=["POST"])
def serve_login():

    redirect_if_already_logged_in()

    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":

        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return '', 422
        
        is_authenticated, errmsg = is_valid_login(db=dbmanager, email=email, password=password)
        
        if is_authenticated:
        
            # lets get the userid
            userid = get_userid_from_email(db=dbmanager, email=email)
            sid = create_session(db=dbmanager, userid=userid, request_obj=request)

            if not userid:
                return render_template("login.html", errmsg="Internal server error: Failed to fetch user")    

            if not sid:
                return render_template("login.html", errmsg="Internal server error: Unable to acquire session ID")

            log.debug("Sending session to client")
            response = make_response(redirect(url_for("index")))
            response.set_cookie(key="sessionID", value=sid)

            return response
        else:
            return render_template("login.html", errormsg=errmsg)

@app.route('/logout')
def logout():
    sid = get_session_id()
    if sid:
        invalidate_session(db=dbmanager, sessionID=sid)

    return redirect(url_for('serve_login'))



@app.route('/profile', methods=["GET", "POST"])
def profile():

    log.debug(is_user_logged_in())
    if not is_user_logged_in():
        abort(401)

    seshid = get_session_id()
    userid = get_userid_from_session(db=dbmanager, sessionID=seshid)
    get_info = dbmanager.read(query_str="""
        SELECT email, username, join_date
        FROM users
        WHERE id = %s
    """, params=(userid,))

    # trunk this into the utility at some point
    email = deep_get(get_info, 0, 0)
    length = len(email) - 3
    hidden_email = email[0:3] + ('*' * length)

    username = deep_get(get_info, 0, 1)
    joinDate = deep_get(get_info, 0, 2)

    userinfo = dict(
        userid = userid,
        username = username,
        join_date = joinDate,
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

def get_is_post_locked(post_num):
    get_locked = dbmanager.read(query_str="""
        SELECT post_locked
        FROM posts
        WHERE id = %s
    """, params=(post_num,))

    is_post_locked = deep_get(get_locked, 0, 0)

    return is_post_locked

@app.route("/forums/<int:post_num>/<content_hint>", methods=["GET"])
@limiter.limit("125 per minute", methods=["GET"])
def serve_post_by_id(post_num, content_hint):
    log.debug("We are viewing a singular post from /forums/%s/%s", post_num, content_hint)

    # get the content hint, if the content hint doesnt match, redirect early.
    view_single, column_names = dbmanager.read(query_str=VIEW_POST_BY_ID, fetch=True, get_columns=True, params=(post_num,))
    get_post = rows_to_dict(view_single, column_names)
    single_post = deep_get(get_post, 0)

    saved_content_hint = single_post.get("url_title")

    if content_hint != saved_content_hint:
        print("Theres no content hint, redirect")
        return redirect( url_for("serve_post_by_id", post_num=post_num, content_hint=saved_content_hint) )
    
    dbmanager.write(query_str='UPDATE posts SET views = views + 1 WHERE id = %s;',
        params=(post_num,))

    # get all the posts replies
    replies_rows, column_names = dbmanager.read(query_str=QUERY_PAGE_REPLIES, get_columns=True, params=(post_num,))
    replies_list = rows_to_dict(replies_rows, column_names)

    # get if the post is locked or not
    is_post_locked = get_is_post_locked(post_num=post_num)

    return render_template("view_post.html", post=single_post, replies=replies_list, is_post_locked=is_post_locked)


# categories are used for seperating mountains of posts by their categoryid
# posts follow no pattern besides externally its postid, and if present its extracted url safe preview
# so, in essence we need a "/forums" but also we need to keep this different from our /postid/hintname
@app.route("/forums", methods=["GET", "POST", "PATCH"])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("80 per minute", methods=["POST"])
def serve_forum():

    if request.method == "GET":

        page_num = request.args.get('page')
        
        log.debug(f"queried post {page_num}")
        try:
            page_num = int(page_num)
            if page_num <= 0:
                raise ValueError("Invalid page number")
        except (TypeError, ValueError):
            # redirect to the first page if page_num is invalid (postgres id starts at 1)
            return redirect(url_for("serve_forum") + "?page=1")

        page_offset = str((page_num - 1) * PAGE_LIMIT)
        log.debug("is the page offset")

        # query the response as json, page the query, include nested replies table
        post_rows, column_names = dbmanager.read(query_str=QUERY_PAGE_POSTS, get_columns=True, params=(str(PAGE_LIMIT), page_offset,))
        posts = rows_to_dict(post_rows, column_names)


    elif request.method == "POST" and request.form.get("_method") == "DELETE":
        reply_id = request.form.get('post_id')
        abort_if_not_signed_in()

        user_id = get_userid_from_session(db=dbmanager, sessionID=get_session_id())
        if not is_admin(user_id):
            return '<p>Unauthorized</p>', 401

        if not reply_id:
            return '<p>Invalid Post ID</p>', 422
        
        get_parent_post_id = dbmanager.write(query_str="""
            UPDATE replies
            SET deleted_at = NOW()
            WHERE id = %s
            RETURNING parent_post_id
        """, fetch=True, params=(reply_id))
        parent_post_id = deep_get(get_parent_post_id, 0, 0)

        log.info("marked reply for deletion")
        return redirect(url_for("serve_post_by_id", post_id=parent_post_id))


    elif request.method == "POST":
        abort_if_not_signed_in()

        is_post_locked = get_is_post_locked()
        if is_post_locked:
            return abort(401)

        # for replies we get the data, and save it nothing more
        post_id = request.form.get('post_id') # hacky way of saving the postid
        reply = request.form.get('reply')

        # minimum of 20 characters in a reply
        # (we can detect spamming later)
        if not post_id or len(reply) <= 5:
            return '<p>Post is too short or invalid post id</p>', 400
        
        sessionID = get_session_id() #guarenteed because of the abort
        author = get_userid_from_session(db=dbmanager, sessionID=sessionID)

        log.debug("creating a reply linked to the parent post")
        dbmanager.write(query_str="INSERT INTO replies (parent_post_id, contents, author) VALUES (%s, %s, %s)",
            params=(post_id, reply, author))

        # redirect back to the view_forum to trigger the refresh
        return redirect(url_for("serve_post_by_id", post_id=post_id))


    return render_template("forums.html", posts=posts)

# here we go....
@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    
    redirect_if_already_logged_in()

    if request.method == "GET":

        # if the user is already signed in, redirect them away
        return render_template("signup.html")
    elif request.method == "POST":
        
        email = request.form.get('email', type=str)
        username = request.form.get('username', type=str)
        password = request.form.get('password', type=str)
        
        if not email or not username or not password:
            return '', 400
        
        userid, errmsg = signup(db=dbmanager, email=email, username=username, password=password)

        if not userid:
            return render_template("signup.html", errmsg=errmsg)
        
        return redirect(url_for("index"))


# for posting we can just reuse this route
@app.route('/post', methods=['GET', 'POST'])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("70 per minute", methods=["POST"])
def submit_new_post():
    abort_if_not_signed_in()

    if request.method == "GET":
        

        return render_template("create_post.html")

    elif request.method == "POST":

        title = request.form.get('title', type=str)
        description = request.form.get('description', type=str)
        
        if not title or not description:
            return '', 400

        sessionID = get_session_id()
        author = get_userid_from_session(db=dbmanager, sessionID=sessionID)

        # now, instead of having to create this every time, lets save it to the db (auto truncates)
        url_safe_title = title_to_content_hint(title)

        retrieved = dbmanager.write(query_str="INSERT INTO posts (title, contents, author, url_title) VALUES (%s, %s, %s, %s) RETURNING id",
            fetch=True,
            params=(title, description, author, url_safe_title,)
        )

        new_post_id = deep_get(retrieved, 0, 0)
        log.debug(new_post_id)
        if new_post_id:
            return redirect(url_for("serve_post_by_id", post_num=new_post_id, content_hint=url_safe_title))

    return '<p>Internal Server Error</p>', 500

@app.route('/static/<path:filename>')
@limiter.exempt
def serve_static(filename):
    return send_from_directory('static', filename)

    