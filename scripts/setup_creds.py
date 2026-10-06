
import json
from multiprocessing import connection
import shutil
import subprocess
import platform
import base64
import os

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
    #print(app_config.db_config)
    #psql = shutil.which("psql")
    # for now im doing the windows branch
    current_os = platform.system()

    db_user = app_config.db_config['user']
    db_database = app_config.db_config['database']
    db_host = app_config.db_config['host']
    db_password = app_config.db_config['password']

    connection_uri = f"postgresql://{db_user}:{db_password}@{db_host}/{db_database}"
    login_psql = None

    if current_os == "Windows":
        # go into wsl, open psql shell and setup users

        login_psql = [
            "wsl",
            "psql", 
            connection_uri
        ]

    elif current_os == "Linux":

        login_psql = [
            "psql", 
            connection_uri
        ]
        
    else:
        print("Currently unsupported platform.")
        return

    # spawn our process
    try:
        process = subprocess.Popen(
            login_psql,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        psql_create_users = (
            f"CREATE USER {app_config.db_config['user']} WITH PASSWORD '{app_config.db_config['password']}';\n"
            f"GRANT ALL PRIVILEGES ON DATABASE {app_config.db_config['database']} TO {app_config.db_config['user']};\n"
            f"SELECT usename FROM pg_user;\n"
            f"\\q\n"
        )

        stdout_data, stderr_data = process.communicate(input=psql_create_users)

        if process.returncode == 0:
            users = [line.strip() for line in stdout_data.splitlines() if line.strip()]
            print("PostgreSQL Users:", users)
        else:
            print(f"Error ({process.returncode}):", stderr_data)
    except Exception as e:
        print("An unexpected error occured while setting up postgresql accounts. Error: ", e)
    finally:
        print("Cleaning up...")
        if 'process' in locals() and process.poll() is None:
            process.kill()
        print("Shell closed.")


def create_secrets():
    if not os.path.exists(ROOT_FOLDER / "secrets.env"):
        # we need to also generate some defaults for our database
        # since this is only a test website, the credentials will be generic
        # generate a new flask secret key
        with open(ROOT_FOLDER / "secrets.env", 'w') as f:
            for key, secret in env.items():
                fmt_str = format_env_key(key, secret)
                f.write(fmt_str)

        print("Wrote secrets.env file")

create_secrets()
create_postgres_users()
