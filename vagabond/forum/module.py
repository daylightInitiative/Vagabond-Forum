from vagabond.utility import deep_get
from vagabond.services import dbmanager




def get_is_post_locked(post_num):
    get_locked = dbmanager.read(query_str="""
        SELECT post_locked
        FROM posts
        WHERE id = %s
    """, params=(post_num,))
    return deep_get(get_locked, 0, 0) or False

def is_user_reply_owner(userid: str, postid: str) -> bool:
    get_is_owner = dbmanager.read(query_str="""
        SELECT EXISTS (
            SELECT 1 FROM replies WHERE author = %s AND id = %s
        );
    """, fetch=True, params=(userid, postid,))
    return deep_get(get_is_owner, 0, 0) or False

def is_user_post_owner(userid: str, postid: str) -> bool:
    get_is_owner = dbmanager.read(query_str="""
        SELECT EXISTS (
            SELECT 1 FROM posts WHERE author = %s AND id = %s
        );
    """, fetch=True, params=(userid, postid,))
    return deep_get(get_is_owner, 0, 0) or False