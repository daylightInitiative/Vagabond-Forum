
import os
import logging
import traceback
import json

from queries import *
from session import create_session, is_valid_session, invalidate_session, get_userid_from_session
from config import Config
from utility import DBManager, rows_to_dict, deep_get, is_valid_email_address, get_userid_from_email
from utility import DB_SUCCESS, DB_FAILURE, EXECUTED_NO_FETCH
from signup import signup
from login import is_valid_login
from logFormatter import CustomFormatter # we love colors

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

def is_user_logged_in():
    sid = request.cookies.get("sessionID")
    return sid and is_valid_session(db=dbmanager, sessionID=sid)

# going to add more high level stuff here, like is_superuser()
def abort_if_unauthorized():
    if not is_user_logged_in():
        abort(401)

def redirect_if_already_logged_in():
    if is_user_logged_in():
        return redirect( url_for("index") )

# great tutorial on the usage of templates
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ii-templates

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
    #db.session.rollback()
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
    num_hits = dbmanager.read(query_str="SELECT hits FROM webstats;")[0][0]

    log.debug("test debug")
    log.info("test info")
    log.warning("test warning")
    log.error("test error")

    return render_template("index.html", number=random_number, num_hits=num_hits)


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

        if email is None or password is None:
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
    #session.clear()

    sid = request.cookies.get("sessionID")
    if sid:
        invalidate_session(db=dbmanager, sessionID=sid)

    return redirect(url_for('serve_login'))

def is_superuser(userid) -> bool:
    get_is_superuser = dbmanager.read(query_str="""
        SELECT id, is_superuser
        FROM users
        WHERE id = %s and is_superuser = TRUE
    """, fetch=True, params=(userid,))
    return deep_get(get_is_superuser, 0, 1) or False
        

# handles displaying the forum and creating replies to posts
@app.route("/forums", methods=["GET", "POST"])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("80 per minute", methods=["POST"])
def serve_forum():

    if request.method == "GET":

        page_num = request.args.get('page')
        post_num = request.args.get('post')

        if post_num and not page_num:

            try:
                post_num = int(post_num)
                if post_num <= 0:
                    raise ValueError("Invalid post number")
            except (TypeError, ValueError):
                # redirect to the first page if page_num is invalid (postgres id starts at 1)
                return redirect(url_for("serve_forum") + "?page=1")
            
            printf("we have visited a post and not a page, dynamically load it")
            # we're going to read from one specific post
            view_single, column_names = dbmanager.read(query_str=VIEW_POST_BY_ID, fetch=True, get_columns=True, params=(post_num,))
            single_post = rows_to_dict(view_single, column_names)[0]
            
            update_views = dbmanager.write(query_str='UPDATE posts SET views = views + 1 WHERE id = %s;',
                params=(post_num,))

            # get all the posts replies
            replies_rows, column_names = dbmanager.read(query_str=QUERY_PAGE_REPLIES, get_columns=True, params=(post_num,))
            replies_list = rows_to_dict(replies_rows, column_names)

            # query if the user is a superuser to delete the replies, and entire post
            is_superuser = False
            sessionID = request.cookies.get("sessionID")

            if sessionID and is_valid_session(db=dbmanager, sessionID=sessionID):
                userid = get_userid_from_session(db=dbmanager, sessionID=sessionID)
                is_superuser = is_superuser(userid)

            return render_template("view_post.html", post=single_post, replies=replies_list, is_superuser=is_superuser)
        
        printf(f"queried post {page_num}")
        try:
            page_num = int(page_num)
            if page_num <= 0:
                raise ValueError("Invalid page number")
        except (TypeError, ValueError):
            # redirect to the first page if page_num is invalid (postgres id starts at 1)
            return redirect(url_for("serve_forum") + "?page=1")

        page_offset = str((page_num - 1) * PAGE_LIMIT)
        printf("is the page offset")
        printf(page_offset)

        # query the response as json, page the query, include nested replies table
        post_rows, column_names = dbmanager.read(query_str=QUERY_PAGE_POSTS, get_columns=True, params=(str(PAGE_LIMIT), page_offset,))
        posts = rows_to_dict(post_rows, column_names)

    elif request.method == "POST":
        abort_if_unauthorized()
        # for replies we get the data, and save it nothing more
        post_id = request.form.get('post_id') # hacky way of saving the postid
        reply = request.form.get('reply')

        # minimum of 20 characters in a reply
        # (we can detect spamming later)
        if post_id is None or len(reply) <= 5:
            return '<p>Post is too short or invalid post id</p>', 400
        
        sessionID = request.cookies.get("sessionID") #guarenteed because of the abort
        author = get_userid_from_session(db=dbmanager, sessionID=sessionID)

        printf(post_id)
        printf("creating a reply linked to the parent post")
        dbmanager.write(query_str="INSERT INTO replies (parent_post_id, contents, author) VALUES (%s, %s, %s)",
            params=(post_id, reply, author))

        # redirect back to the view_forum to trigger the refresh
        return redirect(url_for("serve_forum") + f"?post={post_id}")
    
    elif request.method == "DELETE":
        post_id = request.form.get('post_id')
        abort_if_unauthorized()

        if not post_id:
            return '<p>Invalid Post ID</p>', 422
        

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

    if request.method == "GET":

        # TODO: pass user info into this template like the username and stuff
        return render_template("create_post.html")

    elif request.method == "POST":

        abort_if_unauthorized()
        title = request.form.get('title', type=str)
        description = request.form.get('description', type=str)
        
        if not title or not description:
            return '', 400

        sessionID = request.cookies.get("sessionID")
        author = get_userid_from_session(db=dbmanager, sessionID=sessionID)

        retrieved = dbmanager.write(query_str="INSERT INTO posts (title, contents, author) VALUES (%s, %s, %s) RETURNING id",
            fetch=True, 
            params=(title, description, author,)
        )

        new_post_id = retrieved[0]
        if new_post_id:
            return redirect(f'/forums?post={new_post_id}')

    return '<p>Internal Server Error</p>', 500

@app.route('/static/<path:filename>')
@limiter.exempt
def serve_static(filename):
    return send_from_directory('static', filename)

    