from flask import Blueprint, current_app as app

session_bp = Blueprint('session', __name__)
from . import routes # import the routes from our seperated file