from flask import Blueprint

forum_bp = Blueprint('forum', __name__)
from vagabond.forum.routes import *
from vagabond.forum.posts import *