from flask import Blueprint

signup_bp = Blueprint('signup', __name__)
from vagabond.signup.routes import *