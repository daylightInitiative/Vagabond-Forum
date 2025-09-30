from vagabond.services import dbmanager
from vagabond.utility import deep_get

from enum import Enum, auto
import logging

log = logging.getLogger(__name__)

def is_user_banned():
    pass

def is_admin(userid: str) -> bool:
    get_is_superuser = dbmanager.read(query_str="""
        SELECT is_superuser
        FROM users
        WHERE id = %s
    """, fetch=True, params=(userid,))
    return deep_get(get_is_superuser, 0, 0) or False