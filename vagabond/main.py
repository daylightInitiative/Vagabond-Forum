
import os
import logging as log
import traceback
import json

from queries import *
from config import Config
from utility import DBManager

from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from random import randint

PAGE_LIMIT = 10
load_dotenv()

app = Flask(__name__)
config_path = os.getenv("CONFIG_PATH", "")
if not config_path:
    log.critical("USAGE: CONFIG_PATH=/path/to/config.json")
    quit(1)

with open(config_path, "r") as f:
    config_data = json.load(f)

app_config = Config(config_data)
app.config["custom_config"] = app_config

# create the our db manager
dbmanager = DBManager(app_config)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["400 per hour"],
    storage_options={"socket_timeout": 5},
    storage_uri="memory://localhost:11211",
)

# great tutorial on the usage of templates
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ii-templates

@app.before_request
def log_request_info():
    print(f"[ACCESS] {request.method} {request.path} from {request.remote_addr}")
    if '/static' in request.path: # we dont want resources to count as a website visit
        return
    dbmanager.write(query_str='UPDATE webstats SET hits = hits + 1;')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error_pages/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    #db.session.rollback()
    return render_template('error_pages/500.html'), 500

@app.route("/news.html")
def news():

    # will be fixing the json soon to return just a tuple or dict by RealDictCursor
    news_feed = dbmanager.read(query_str=QUERY_NEWS_POSTS, fetch=True)[0][0]

    return render_template("news.html", news_feed=news_feed or [])

@app.route("/reading_list.html")
def reading_list():
    return render_template("reading.html")

@app.route("/")
def index():
    random_number = randint(1, 99999)
    num_hits = dbmanager.read(query_str="SELECT hits FROM webstats;")[0][0]

    return render_template("index.html", number=random_number, num_hits=num_hits)




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

            print("we have visited a post and not a page, dynamically load it")
            # we're going to read from one specific post
            single_post = dbmanager.read(query_str=VIEW_POST_BY_ID, fetch=True, params=(post_num,))[0][0][0]

            dbmanager.write(query_str='UPDATE posts SET views = views + 1 WHERE id = %s;',
                params=(post_num,))

            # get all the posts replies
            replies_list = dbmanager.read(query_str=QUERY_PAGE_REPLIES, params=(post_num,))[0][0]
            #print(replies_list, single_post, post_num)

            return render_template("view_post.html", post=single_post, replies=replies_list)
        
        print(f"queried post {page_num}")
        try:
            page_num = int(page_num)
            if page_num <= 0:
                raise ValueError("Invalid page number")
        except (TypeError, ValueError):
            # redirect to the first page if page_num is invalid (postgres id starts at 1)
            return redirect(url_for("serve_forum") + "?page=1")

        page_offset = str((page_num - 1) * PAGE_LIMIT)
        print(page_offset, "is the page offset")

        # query the response as json, page the query, include nested replies table
        posts = dbmanager.read(query_str=QUERY_PAGE_POSTS, params=(str(PAGE_LIMIT), page_offset,))[0][0]
        #print(posts)

    elif request.method == "POST":
        # for replies we get the data, and save it nothing more
        post_id = request.form.get('post_id') # hacky way of saving the postid
        reply = request.form.get('reply')

        # minimum of 20 characters in a reply
        # (we can detect spamming later)
        if post_id is None or len(reply) <= 5:
            return '<p>Post is too short or invalid post id</p>', 400
        
        # no logging in yet author is just Anon
        author = "Anon"

        print(post_id)
        print("creating a reply linked to the parent post")
        dbmanager.write(query_str="INSERT INTO replies (parent_post_id, contents, author) VALUES (%s, %s, %s)",
            params=(post_id, reply, author))

        # redirect back to the view_forum to trigger the refresh
        return redirect(url_for("serve_forum") + f"?post={post_id}")

    return render_template("forums.html", posts=posts)

# for posting we can just reuse this route
@app.route('/post', methods=['GET', 'POST'])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("70 per minute", methods=["POST"])
def submit_new_post():

    if request.method == "GET":

        # TODO: pass user info into this template like the username and stuff
        return render_template("create_post.html")

    elif request.method == "POST":

        title = request.form.get('title', type=str)
        description = request.form.get('description', type=str)
        
        if not title or not description:
            return '', 400

        author = "Anon"
        retrieved = dbmanager.write(query_str="INSERT INTO posts (title, contents, author) VALUES (%s, %s, %s) RETURNING id",
            fetch=True, 
            params=(title, description, author)
        )

        new_post_id = retrieved[0]
        if new_post_id:
            return redirect(f'/forums?post={new_post_id}')

    return '<p>Internal Server Error</p>', 500

@app.route('/static/<path:filename>')
@limiter.exempt
def serve_static(filename):
    return send_from_directory('static', filename)

@app.cli.command("testdb")
def poke_at_postgresql():

    db_version = dbmanager.write(query_str=SHOW_SERVER_VERSION, fetch=True)
    print("Running: ", db_version[0][0])
    dbmanager.write(INIT_DB_TABLES)
    