
import os
import psycopg2 as post # for connecting to postgresql
import click
import json
import re

from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from random import randint

load_dotenv()

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour"],
    storage_options={"socket_timeout": 5},
    storage_uri="memory://localhost:11211",
)

# great tutorial on the usage of templates
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ii-templates

DB_CONFIG = {
    "host": "127.0.0.1",
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": "5432"
}

def read_sql_file(filename):
    with open(filename, mode='r') as f:
        filetext = f.read()
        return filetext


@app.before_request
def log_request_info():
    print(f"[ACCESS] {request.method} {request.path} from {request.remote_addr}")
    # need to update the hits by one
    if '/static' in request.path: # we dont want resources to count as a website visit
        return
    try:
        with post.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE webstats SET hits = hits + 1;')
                conn.commit()

    except post.Error as e:
        print(f"An error occured: {e}")

@app.route("/news.html")
def news():
    return render_template("news.html")

@app.route("/reading_list.html")
def reading_list():
    return render_template("reading.html")

@app.route("/")
def index():
    # serve a random number to the template
    random_number = randint(1, 99999)

    # get the number of website hits
    num_hits = 0
    with post.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT hits FROM webstats;")
                num_hits = cur.fetchall()[0][0]
                print(num_hits)

    return render_template("index.html", number=random_number, num_hits=num_hits)

PAGE_LIMIT = 10


@app.route("/forums", methods=["GET", "POST"])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("80 per minute", methods=["POST"])
def serve_forum():
    try:
        with post.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:

                if request.method == "GET":

                    page_num = request.args.get('page')
                    post_num = request.args.get('post')

                    if page_num is None and post_num:

                        print("we have visited a post and not a page, dynamically load it")
                        # we're going to read from one specific post
                        query_singular_post_cmd = read_sql_file("view_post_by_num.sql")
                        cur.execute(query_singular_post_cmd, (post_num,))
                        single_post = cur.fetchall()[0][0][0]
                        #print(single_post)

                        # lets increment the views on this post
                        cur.execute('UPDATE posts SET views = views + 1 WHERE id = %s;', (post_num))

                        # get all the posts replies
                        query_post_replies = read_sql_file("query_page_replies.sql")
                        cur.execute(query_post_replies, (post_num,))
                        replies_list = cur.fetchall()[0][0]
                        print(replies_list)

                        return render_template("view_post.html", post=single_post, replies=replies_list)
                    
                    print(f"queried post {page_num}")
                    if not page_num:
                        # one can not simply visit /forum we redirect to the default if they do
                        return redirect(url_for("serve_forum") + "?page=1")
                    page_num = int(page_num)

                    page_offset = str((page_num - 1) * PAGE_LIMIT)
                    print(page_offset, "is the page offset")

                    # query the response as json, order by created at time and limit it by 10 with the offset
                    query_posts_cmd = read_sql_file("query_page_posts.sql")
                    cur.execute(query_posts_cmd, (page_offset,))
                    posts = cur.fetchall()[0][0]
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

                    # parent_post_id, contents, author,
                    print("creating a reply linked to the parent post")
                    cur.execute("INSERT INTO replies (parent_post_id, contents, author) VALUES (%s, %s, %s)",
                        (post_id, reply, author))
                    conn.commit()

                    # return back to the view forum to trigger the refresh
                    return redirect(url_for("serve_forum") + f"?post={post_id}")
        # before we render the template we need to get the number of replies mapped to the posts in posts
        # TODO: JOIN the replies with the 
        # we have to get the replies and add them into the posts dict



    except Exception as e:
        print(f"An error occured: {e}")
        return '', 400

    return render_template("forums.html", posts=posts)


# all this clowning around with formatting is a thing of the past


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
        with post.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO posts (title, contents, author) VALUES (%s, %s, %s) RETURNING id",
                            (title, description, author))
                new_post_id = cur.fetchone()[0]
                #print(new_post_id)
                conn.commit()
                # return in here

                return redirect(f'/forums?post={new_post_id}')

        # if we use RETURNING it gives us the created id
        

        # for right now the author is anon
        #return '<p>post submitted...</p>', 200
        #return redirect(url_for('index')), 302

@app.route('/static/<path:filename>')
@limiter.exempt
def serve_static(filename):
    return send_from_directory('static', filename)

@app.cli.command("testdb")
def poke_at_postgresql():
    try:
        with post.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute('SHOW server_version;')
                db_version = cursor.fetchone()
                print("Running: " + db_version[0])
                commands = read_sql_file("create_stats_table.sql")
                cursor.execute(commands)
                #print(commands)
                conn.commit()

    except Exception as err:
        print(f"An error occured: {err}")
    