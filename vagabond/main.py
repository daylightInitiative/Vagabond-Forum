
import os
import psycopg2 as post # for connecting to postgresql
import click 
from flask import Flask, jsonify, request, render_template
from random import randint
#from dotenv import load_dotenv

#load_dotenv()

app = Flask(__name__)

# great tutorial on the usage of templates
# https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-ii-templates

DB_CONFIG = {
    "host": "127.0.0.1",
    "database": "forum",
    "user": "admin",
    "password": "root",
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
    except post.Error:
        print(f"An error occured: {e}")

@app.route('/post', methods=['POST'])
def submit_new_post():
    name = request.form.get('title', type=str)
    description = request.form.get('description', type=str)
    
    author = "Anon"

    conn = post.connect(**DB_CONFIG)

    with conn.cursor() as cur:
        cur.execute("INSERT INTO posts (contents, author) VALUES (%s, %s)",
                    (description, author))
        conn.commit()

    conn.close()

    # for right now the author is anon
    return '<p>post submitted...</p>', 200

@app.route("/")
def index():
    # serve a random number to the template
    random_number = randint(1, 99999)
    return render_template("index.html", number=random_number)

# all this clowning around with formatting is a thing of the past


def read_sql_file(filename):
    with open(filename, mode='r') as f:
        filetext = f.read()
        return filetext
        


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

    except post.Error as e:
        print(f"An error occured: {e}")
    