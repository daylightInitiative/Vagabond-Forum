from vagabond.utility import deep_get
from vagabond.services import dbmanager
import logging

log = logging.getLogger(__name__)

def get_is_category_locked(categoryID: str) -> bool:
    get_locked = dbmanager.read(query_str="""
        SELECT category_locked
        FROM categories
        WHERE id = %s
    """, params=(categoryID,))
    return deep_get(get_locked, 0, 0) or False

def get_is_post_locked(post_num: str) -> bool:
    get_locked = dbmanager.read(query_str="""
        SELECT post_locked
        FROM posts
        WHERE id = %s
    """, params=(post_num,))
    return deep_get(get_locked, 0, 0) or False


def is_user_content_owner(post_type:str, userid: str, postid: str) -> bool:

    table = ""
    if post_type == "post": table = "posts"
    elif post_type == "reply": table = "replies"
    else:
        log.error("Invalid post type: passed to is_user_content_owner")
        return None

    # since id and author is standardized across tables we can simply fstring it
    check_owner = f"""
        SELECT EXISTS (
            SELECT 1 FROM {table} WHERE author = %s AND id = %s
        );
    """

    get_is_owner = dbmanager.read(query_str=check_owner, fetch=True, params=(userid, postid,))
    return deep_get(get_is_owner, 0, 0) or False