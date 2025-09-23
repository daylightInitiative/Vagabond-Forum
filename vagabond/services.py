from vagabond.dbmanager import DBManager, DBStatus
from vagabond.config import app_config

from flask import current_app as app # flask stores the global app as current_app automatically


dbmanager = DBManager(app_config)