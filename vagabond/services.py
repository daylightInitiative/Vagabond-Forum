from vagabond.dbmanager import DBManager, DBStatus
from vagabond.config import app_config
from flask_limiter import Limiter

from flask import current_app as app # flask stores the global app as current_app automatically
from flask_limiter.util import get_remote_address
from flask_moment import Moment

# intstantiate all of our service objects here (to avoid mass passing into functions)
moment = Moment() # flask_moment does the fluff of handling local timezones.

limiter = Limiter(
    get_remote_address,
    default_limits=["400 per hour"],
    storage_options={"socket_timeout": 5},
    storage_uri="memory://localhost:11211",
)

dbmanager = DBManager(app_config)

# init_app is a function all flask extensions have, to keep this approach we call it directly to avoid creating instances in main
def init_extensions(app):
    moment.init_app(app)
    limiter.init_app(app)