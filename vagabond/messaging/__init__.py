from flask import Blueprint

messaging_bp = Blueprint('messaging', __name__)
from vagabond.messaging.routes import *