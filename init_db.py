
import os, json
from vagabond.utility import DBManager
from vagabond.config import Config
from vagabond.queries import *

# populates the empty database with the needed tables if not exists
# (not part of the app but uses some components)

config_path = os.getenv("CONFIG_PATH", "")
if not config_path:
    print("USAGE: CONFIG_PATH=/path/to/config.json")
    quit(1)

with open(config_path, "r") as f:
    config_data = json.load(f)

app_config = Config(config_data)
dbmanager = DBManager(app_config)

# this is idiot safe (the tables only create if they IF NOT EXISTS)
# just used in development

if __name__ == '__main__':
    db_version = dbmanager.write(query_str=SHOW_SERVER_VERSION, fetch=True)
    print("Running: ", db_version[0][0])
    dbmanager.write(INIT_DB_TABLES)
    print("Wrote all needed tables")