
import os, json, sys
from vagabond.dbmanager import DBManager
from vagabond.config import Config
from vagabond.queries import *

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vagabond'))
sys.path.insert(0, project_path)

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
    confirm = input("Are you sure you want to wipe all tables in the db (development purposes only): (y/yes)").lower()

    if confirm == "y" or confirm == "yes":
        dbmanager.write(query_str="""
                DO $$ 
            DECLARE 
                r RECORD;
            BEGIN 
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP; 
            END $$;
        """)
        print("Wiped all needed tables")