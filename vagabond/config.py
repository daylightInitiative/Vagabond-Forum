from flask import current_app as app
import logging
import json
import os

# special thanks to chatbot
log = logging.getLogger(__name__)

# returns the configuration as a json string
def _load_config() -> str:
    config_path = os.getenv("CONFIG_PATH", "")
    if not config_path:
        log.critical("USAGE: CONFIG_PATH=/path/to/config.json")
        quit(1)

    with open(config_path, "r") as f:
        config_data = json.load(f)
        return config_data


class Config():
    export_base_dir = None
    models_dir = None
    log_level = "DEBUG"
    db_config = None

    def __init__(self, app=None, data=None):
        config_path = os.getenv("CONFIG_PATH", "")
        log.warning("[+] Loaded configuration file: %s", config_path) # important for debugging to know which config

        self.patch(data)
        self.patch_secrets()
        # change app configuration
        if app:
            app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
            app.config["SECURITY_PASSWORD_SALT"] = os.getenv("SECURITY_PASSWORD_SALT")

    def patch(self, data):
        if data is not None and type(data) is dict:
            fields = [
                "export_base_dir",
                "models_dir",
                "file_log_level",
                "console_log_level",
                "db_config",
                "flask_config",
                "smtp_config"
            ]
            for field in fields:
                if field in data:
                    setattr(self, field, data[field])
    
    def patch_secrets(self):
        # (avoiding putting the password and user in plaintext json files)
        user = os.getenv("DB_USER")
        if user:
            self.db_config["user"] = user

        password = os.getenv("DB_PASSWORD")
        if password:
            self.db_config["password"] = password

app_config = Config(app=app, data=_load_config())