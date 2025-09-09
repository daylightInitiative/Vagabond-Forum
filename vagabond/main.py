
import os
import psycopg2 as post # for connecting to postgresql
import click 
from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory
from random import randint
import json
import re
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


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
    try:
        with post.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE webstats SET hits = hits + 1;')
                conn.commit()

    except post.Error as e:
        print(f"An error occured: {e}")

@app.route("/reading_list.html")
def reading_list():
    return render_template("reading.html")

@app.route("/")
def index():
    # serve a random number to the template
    random_number = randint(1, 99999)

    
    # get the forum posts as a json format and convert to python
    try:
        with post.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT json_agg(t.*) FROM posts AS t;")
                posts = cur.fetchall()[0][0]
                print(posts)

        # lets load the forum posts in a table
    except Exception as e:
        print(f"An error occured: {e}")
        return '', 400

    return render_template("index.html", number=random_number, posts=posts)

PAGE_LIMIT = 10


@app.route("/forums", methods=["GET", "POST"])
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
                    if post_id is None or len(reply) <= 25:
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

                    


    except Exception as e:
        print(f"An error occured: {e}")
        return '', 400

    return render_template("forums.html", posts=posts)


# all this clowning around with formatting is a thing of the past

#@app.route('/forums?post=<code>?reply')


@app.route('/post', methods=['POST'])
def submit_new_post():
    title = request.form.get('title', type=str)
    description = request.form.get('description', type=str)
    
    if not title or not description:
        return '', 400

    author = "Anon"
    with post.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO posts (title, contents, author) VALUES (%s, %s, %s)",
                        (title, description, author))
            conn.commit()

    # for right now the author is anon
    #return '<p>post submitted...</p>', 200
    return redirect(url_for('index')), 302

@app.route('/static/<path:filename>')
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
    