
import base64
import json
import os
from vagabond.dbmanager import DBManager
from vagabond.config import Config
from vagabond.queries import *
from vagabond.utility import deep_get, generate_random_password, ROOT_FOLDER
from generate_hash import create_hash
from vagabond.avatar import create_user_avatar, update_user_avatar
from vagabond.profile.module import create_profile

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

def format_env_key(key, value):
    return f'\n{key}="{value}"'

if __name__ == '__main__':
    db_version = dbmanager.write(query_str=SHOW_SERVER_VERSION, fetch=True)
    print("Running: ", db_version[0][0])
    dbmanager.write(query_str=INIT_DB_TABLES)
    print("Wrote all needed tables")

    # if this was prod i would use load_dotenv (it makes it harder to deploy to test docker instance for others to repro)
    # secrets.env is for our webserver, while the other .env file is used for the docker container
    env = {
        "SECRET_KEY": base64.b64encode(os.urandom(24)).decode('utf-8'),
        "SECURITY_PASSWORD_SALT": base64.b64encode(os.urandom(24)).decode('utf-8')
    }

    # generate a new flask secret key
    with open("secrets.env", 'w') as f:
        
        for key, secret in env.items():
            fmt_str = format_env_key(key, secret)
            f.write(fmt_str)

    users_config = ROOT_FOLDER / "users.json"

    with open(users_config, "r") as f:
        config_data = json.load(f)

        for user in config_data:

            email = user.get("email")
            username = user.get("username")
            raw_password = user.get("password", generate_random_password(15)) # TODO: parsing of csv? or xlsx
            is_superuser = user.get("superuser", False)

            hashstr, saltstr = create_hash(raw_password)

            # email, username, account_locked, loginAttempts, is_online, hashed_password, is_superuser
            get_userid = dbmanager.write(query_str=INIT_SITE_ACCOUNTS, fetch=True, params=(
                email, username, False, False, hashstr, saltstr, is_superuser,))
            
            new_user_id = int(deep_get(get_userid, 0, 0))
            # create admins avatar
            new_avatar = create_user_avatar(userid=new_user_id)
            update_user_avatar(userID=new_user_id, avatar_hash=new_avatar)
            create_profile(userID=new_user_id)

    print("Setup all pre registered accounts")
    categories_config = ROOT_FOLDER / "categories.json"

    # create all default categories dynamically
    with open(categories_config, "r") as f:
        config_data = json.load(f)

        for cat_dict in config_data:
            
            name = cat_dict.get("category_name")
            admin_locked = cat_dict.get("admin_locked", False)

            dbmanager.write(query_str="""
                INSERT INTO categories (name, category_locked)
                    VALUES (%s, %s)
            """, params=(name, admin_locked))

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

    # create some bs news stuff
    dbmanager.write(query_str="""
        INSERT INTO news_feed (title, contents, pinned, author)
            VALUES (%s, %s, %s, %s)
    """, params=("Welcome survivors", "Current news, updates and announcements from our wonderful staff or developers will appear here, stop by to see important information about the current state of the forum.", False, 1))
    