from flask import Blueprint

admin_bp = Blueprint('admin', __name__)
from vagabond.admin.routes import *