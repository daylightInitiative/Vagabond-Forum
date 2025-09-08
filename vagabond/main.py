
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


@app.route("/forums")
def serve_forum():
    try:
        with post.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:

                page_num = request.args.get('page')
                post_num = request.args.get('post')

                if page_num is None and post_num:

                    print("we have visited a post and not a page, dynamically load it")
                    # we're going to read from one specific post
                    query_singular_post_cmd = read_sql_file("view_post_by_num.sql")
                    cur.execute(query_singular_post_cmd, (post_num))
                    single_post = cur.fetchall()[0][0]
                    print(single_post)

                    return render_template("forums.html", post=single_post)
                
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
                print(posts)

    except Exception as e:
        print(f"An error occured: {e}")
        return '', 400

    return render_template("forums.html", posts=posts)


# all this clowning around with formatting is a thing of the past




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
    