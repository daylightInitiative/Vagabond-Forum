from flask import Blueprint

session_bp = Blueprint('session', __name__)
from vagabond.sessions.routes import *