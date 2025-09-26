from vagabond.utility import deep_get, rows_to_dict
from vagabond.services import dbmanager

def get_is_post_locked(post_num):
    get_locked = dbmanager.read(query_str="""
        SELECT post_locked
        FROM posts
        WHERE id = %s
    """, params=(post_num,))

    is_post_locked = deep_get(get_locked, 0, 0)

    return is_post_locked

def is_user_post_owner(userid, postid) -> bool:
    get_is_owner = dbmanager.read(query_str="""
        SELECT id, author
        FROM posts
        WHERE 
    """, fetch=True, params=(userid, postid,))
    return deep_get(get_is_owner, 0, 1) or False

def is_admin(userid) -> bool:
    get_is_superuser = dbmanager.read(query_str="""
        SELECT id, is_superuser
        FROM users
        WHERE id = %s
    """, fetch=True, params=(userid,))
    return deep_get(get_is_superuser, 0, 1) or False