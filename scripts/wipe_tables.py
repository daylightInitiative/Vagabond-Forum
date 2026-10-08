
import os, json, sys

from scripts.pgshell import run_psql_cmd
from vagabond.config import Config

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vagabond'))
sys.path.insert(0, project_path)

# populates the empty database with the needed tables if not exists
# (not part of the app but uses some components)

# this is idiot safe (the tables only create if they IF NOT EXISTS)
# just used in development

config_path = os.getenv("CONFIG_PATH", "")
if not config_path:
    print("USAGE: CONFIG_PATH=/path/to/config.json")
    quit(1)

with open(config_path, "r") as f:
    config_data = json.load(f)

app_config = Config(data=config_data)

def wipe_database_tables():
    print("Creating postgresql users")

    db_user = app_config.db_config['user']
    db_database = app_config.db_config['database']
    db_host = app_config.db_config['host']
    db_password = app_config.db_config['password']

    psql_create_users = [
        """
        DO $$ 
        DECLARE 
            r RECORD;
        BEGIN 
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP 
                EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE'; 
            END LOOP; 
        END $$;
        """,
        "SHOW server_version",
        "SELECT username FROM pg_user\n"
    ]

    pgopts = {
        "user": db_user,
        "database": db_database,
        "host": db_host,
        "password": db_password
    }

    run_psql_cmd(pgopts, psql_create_users)

wipe_database_tables()