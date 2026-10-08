
import json
import base64
import os

from scripts.pgshell import run_psql_cmd
from vagabond.config import Config
from vagabond.utility import ROOT_FOLDER

config_path = os.getenv("CONFIG_PATH", "")
if not config_path:
    print("USAGE: CONFIG_PATH=/path/to/config.json")
    quit(1)

with open(config_path, "r") as f:
    config_data = json.load(f)

app_config = Config(data=config_data)

def format_env_key(key, value):
    return f'\n{key}="{value}"'

env = {
    "SECRET_KEY": base64.b64encode(os.urandom(24)).decode('utf-8'),
    "SECURITY_PASSWORD_SALT": base64.b64encode(os.urandom(24)).decode('utf-8'),
    "POSTGRES_USER": "admin",
    "POSTGRES_PASSWORD": "root",
    "POSTGRES_DB": "forum"
}

def create_postgres_users():
    print("Creating postgresql users")

    db_user = app_config.db_config['user']
    db_database = app_config.db_config['database']
    db_host = app_config.db_config['host']
    db_password = app_config.db_config['password']

    psql_create_users = [
        f"CREATE USER {app_config.db_config['user']} WITH PASSWORD '{app_config.db_config['password']}'",
        f"GRANT ALL PRIVILEGES ON DATABASE {app_config.db_config['database']} TO {app_config.db_config['user']}",
        "SELECT username FROM pg_user"
    ]

    pgopts = {
        "user": db_user,
        "database": db_database,
        "host": db_host,
        "password": db_password
    }

    run_psql_cmd(pgopts, psql_create_users)


def create_secrets():
    file_path = ROOT_FOLDER / "secrets.env"
    if os.path.exists(file_path):
        # we need to also generate some defaults for our database
        # since this is only a test website, the credentials will be generic
        # generate a new flask secret key
        print("Purged old secrets.env file")
        file_path.unlink(missing_ok=True)
    with open(file_path, 'w') as f:
        for key, secret in env.items():
            fmt_str = format_env_key(key, secret)
            f.write(fmt_str)

    print("Wrote secrets.env file")
        

create_secrets()
create_postgres_users()
