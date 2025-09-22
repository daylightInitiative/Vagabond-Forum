
import os, json
from vagabond.utility import DBManager
from vagabond.config import Config
from vagabond.queries import *
from dotenv import load_dotenv

load_dotenv()

# populates the empty database with the needed tables if not exists
# (not part of the app but uses some components)

config_path = os.getenv("CONFIG_PATH", "")
if not config_path:
    print("USAGE: CONFIG_PATH=/path/to/config.json")
    quit(1)

with open(config_path, "r") as f:
    config_data = json.load(f)

app_config = Config(data=config_data)
dbmanager = DBManager(app_config)

# this is idiot safe (the tables only create if they IF NOT EXISTS)
# just used in development

if __name__ == '__main__':
    db_version = dbmanager.write(query_str=SHOW_SERVER_VERSION, fetch=True)
    print("Running: ", db_version[0][0])
    dbmanager.write(query_str=INIT_DB_TABLES)
    print("Wrote all needed tables")

    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    admin_salt = os.getenv("ADMIN_SALT")
    john_salt = os.getenv("JOHN_SALT")

    # email, username, account_locked, loginAttempts, is_online, hashed_password, is_superuser
    dbmanager.write(query_str=INIT_SITE_ACCOUNTS, params=(
        admin_email, "admin", False, False, admin_password, admin_salt, True,))
    
    john_password = os.getenv("JOHN_PASSWORD")
    # lets create a test user to test out banning/account locking
    dbmanager.write(query_str=INIT_SITE_ACCOUNTS, params=(
        "john@example.com", "johnd", True, False, john_password, john_salt, False,))
    print("Setup all pre registered accounts")

    # create some starter categories
    dbmanager.write(query_str="""
        INSERT INTO categories (name)
            VALUES (%s)
    """, params=("Announcements",))

    dbmanager.write(query_str="""
        INSERT INTO categories (name)
            VALUES (%s)
    """, params=("Bushcraft Tips",))

    dbmanager.write(query_str="""
        INSERT INTO categories (name)
            VALUES (%s)
    """, params=("Help & Support",))

    # create some dummy posts
    dbmanager.write(query_str="""
        INSERT INTO posts (category_id, title, contents, author, url_title)
            VALUES (%s, %s, %s, %s, %s)
    """, params=(1, "Welcome to the forum!", "This forum is about survival, backpacking and hunting!", 1, "welcome-to-the-forum"))

    dbmanager.write(query_str="""
        INSERT INTO posts (category_id, title, contents, author, url_title)
            VALUES (%s, %s, %s, %s, %s)
    """, params=(2, "Basic Pack Setup", "A good pack is small, and purpose driven make sure to always carry water filtering equipment", 1, "basic-pack-setup"))
    
    dbmanager.write(query_str="""
        INSERT INTO posts (category_id, title, contents, author, url_title)
            VALUES (%s, %s, %s, %s, %s)
    """, params=(2, "Reach out to us", "We are super friendly", 1, "reach-out-to-us"))
    