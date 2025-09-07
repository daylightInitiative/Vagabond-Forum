
import os
import psycopg2 as post # for connecting to postgresql
import click 
from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory
from random import randint
import json
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

@app.before_request
def log_request_info():
    print(f"[ACCESS] {request.method} {request.path} from {request.remote_addr}")
    # need to update the hits by one
    try:
        conn = post.connect(**DB_CONFIG)

        with conn.cursor() as cursor:
            cursor.execute('UPDATE webstats SET hits = hits + 1;')
            conn.commit()

        conn.close()
    except post.Error as e:
        print(f"An error occured: {e}")


@app.route("/")
def index():
    # serve a random number to the template
    random_number = randint(1, 99999)

    
    # get the forum posts as a json format and convert to python
    try:
        conn = post.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("SELECT json_agg(t.*) FROM posts AS t;")
        posts = cur.fetchall()[0][0]
        print(posts)
        
        
        cur.close()
        conn.close()

        # lets load the forum posts in a table
    except Exception as e:
        print(f"An error occured: {e}")
        return '', 400

    return render_template("index.html", number=random_number, posts=posts)

# all this clowning around with formatting is a thing of the past

def read_sql_file(filename):
    with open(filename, mode='r') as f:
        filetext = f.read()
        return filetext


@app.route('/post', methods=['POST'])
def submit_new_post():
    title = request.form.get('title', type=str)
    description = request.form.get('description', type=str)
    
    if not title or not description:
        return '', 400

    author = "Anon"

    conn = post.connect(**DB_CONFIG)

    with conn.cursor() as cur:
        cur.execute("INSERT INTO posts (title, contents, author) VALUES (%s, %s, %s)",
                    (title, description, author))
        conn.commit()

    conn.close()

    # for right now the author is anon
    #return '<p>post submitted...</p>', 200
    return redirect(url_for('index')), 302

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.cli.command("testdb")
def poke_at_postgresql():
    try:
        conn = post.connect(**DB_CONFIG)

        with conn.cursor() as cursor:
            cursor.execute('SHOW server_version;')
            db_version = cursor.fetchone()
            print("Running: " + db_version[0])
            commands = read_sql_file("create_stats_table.sql")
            cursor.execute(commands)
            #print(commands)
            conn.commit()
        conn.close()

    except Exception as err:
        print(f"An error occured: {err}")
    