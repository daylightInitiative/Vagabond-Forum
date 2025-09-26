from flask import Blueprint

login_bp = Blueprint('login', __name__)
from vagabond.login.routes import *