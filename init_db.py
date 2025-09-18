
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