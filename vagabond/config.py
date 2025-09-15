from dotenv import load_dotenv
import json
import os

load_dotenv()

# special thanks to chatbot

class Config():
    export_base_dir = None
    models_dir = None
    log_level = "DEBUG"
    db_config = None

    def __init__(self, app=None, data=None):
        self.patch(data)
        self.patch_secrets()
        # change app configuration
        if app:
            app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

    def patch(self, data):
        if data is not None and type(data) is dict:
            fields = [
                "export_base_dir",
                "models_dir",
                "log_level",
                "db_config"
            ]
            for field in fields:
                if field in data:
                    setattr(self, field, data[field])
    
    def patch_secrets(self):
        # (avoiding putting the password in plaintext json files)
        password = os.getenv("DB_PASSWORD")
        if password:
            self.db_config["password"] = password
