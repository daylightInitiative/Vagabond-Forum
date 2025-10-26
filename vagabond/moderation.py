from multiprocessing import Value
from vagabond.constants import SYSTEM_ACCOUNT_ID, PostType, UserRole, ModerationAction
from vagabond.services import dbmanager as db
from vagabond.utility import deep_get, get_groupid_from_message, is_valid_userid
from vagabond.sessions.module import get_session_id, get_userid_from_session
from flask import abort, redirect, url_for, jsonify

from functools import wraps
from enum import Enum, auto, StrEnum
import logging

log = logging.getLogger(__name__)

def get_role_from_userid(userid: str) -> UserRole | None:

    if not userid:
        return None

    has_role = db.read(query_str="""
        SELECT user_role
        FROM users
        WHERE id = %s
    """, params=(userid,))
    current_role = deep_get(has_role, 0, 0)

    if not current_role:
        log.warning("Failure to fetch user role '%s' info for userid: %s", current_role, userid)
        return None

    role_to_return = None
    try:
        role_to_return = UserRole(current_role)
    except ValueError as e:
        log.error("Failure converting user role into a UserPermission")
        return None

    return role_to_return

def has_permission(userid: str, roles:list[UserRole]) -> bool:
    return True if get_role_from_userid(userid) in roles else False

""" Decorator that checks if a user has authentication for a given route, with the new roles system
    @requires_permission([UserPermission.ADMIN, ...])
      Note: It is recomended to alias the user permissions for readability """
def requires_permission(roles: list[UserRole]):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            sid = get_session_id()
            user_id = get_userid_from_session(sessionID=sid)

            if not user_id:
                return redirect(url_for("login.serve_login"))

            user_role = get_role_from_userid(user_id)

            if user_role not in roles:
                return abort(403)

            return f(*args, **kwargs)
        return wrapped
    return decorator




def is_admin(userid: str) -> bool:
    return has_permission(userid=userid, roles=[UserRole.ADMIN, UserRole.MODERATOR])

def manage_user_ban(userid: str, is_banned: bool, admin_userid: str | None = None, reason: str | None = None) -> None:
    admin_userid = admin_userid or SYSTEM_ACCOUNT_ID
        
    is_banned = not is_banned

    if not userid or not is_valid_userid(userID=userid):
        log.warning("Invalid userid")
        return None
    
    if not is_admin(userid=admin_userid):
        log.warning("Invalid permissions for admin_userid")
        return None
    
    db.write(query_str="""
        UPDATE users
        SET account_locked = %s
        WHERE id = %s
    """, params=(is_banned, userid,))

    modaction = ModerationAction.BAN_USER.value if is_banned else ModerationAction.UNBAN_USER.value

    db.write(query_str="""
        INSERT INTO moderation_actions (action, target_user_id, performed_by, reason, created_at)
            VALUES (%s, %s, %s, %s, NOW())
    """, params=(
        modaction,
        userid,
        admin_userid, # "SYSTEM" user
        reason
    ))

def is_valid_user_role(user_role: str) -> bool:
    try:
        exists = UserRole(user_role)
    except ValueError:
        return False
    
    return True

def change_role(userid: str, user_role: UserRole, admin_userid: str | None = None) -> None:
    admin_userid = admin_userid or SYSTEM_ACCOUNT_ID

    if not userid or admin_userid:
        log.warning("Invalid username(s) passed, [admin=%s, user=%s]", admin_userid, userid)
        return None

    if not is_valid_user_role(user_role):
        log.warning("Invalid role %s passed to is_valid_role", user_role)
        return None

    db.write(query_str="""
        INSERT INTO moderation_actions (action, target_user_id, performed_by, reason, created_at)
            VALUES (%s, %s, %s, %s, NOW())
    """, params=(
        ModerationAction.CHANGE_ROLE.value,
        userid,
        admin_userid,
        "System automated action"
    ))

    db.write(query_str="""
        UPDATE users
        SET user_role = %s
        WHERE id = %s
    """, params=(user_role, userid,))

    return None

# i dont see any reason to "unhellban someone"
def hellban_user(userid: str, admin_userid: str | None = None, reason: str | None = None) -> None: # interesting way of optional arguments with type checking
    admin_userid = admin_userid or SYSTEM_ACCOUNT_ID

    if not userid or not is_valid_userid(userID=userid):
        log.warning("Invalid userid")
        return None
    
    if not is_admin(userid=admin_userid):
        log.warning("Invalid permissions for admin_userid")
        return None

    # hellban user
    db.write(query_str="""
        INSERT INTO shadow_bans (userid)
            VALUES (%s) ON CONFLICT (userid) DO NOTHING
    """, params=(userid,))

    # add to moderation actions
    # action VARCHAR(255) NOT NULL,
    # target_user_id INTEGER NOT NULL,
    # target_post_id INTEGER,
    # performed_by INTEGER NOT NULL,
    # reason VARCHAR(2048) DEFAULT 'No reason specified.',
    # created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    # expires_at TIMESTAMP,
    # reverted_by INTEGER,
    # reverted_at TIMESTAMP,

    db.write(query_str="""
        INSERT INTO moderation_actions (action, target_user_id, performed_by, reason, created_at)
            VALUES (%s, %s, %s, %s, NOW())
    """, params=(
        ModerationAction.SHADOWBAN_USER.value,
        userid,
        admin_userid, # "SYSTEM" user
        reason
    ))

    return None


def soft_delete_user_post(post_type: PostType, post_id: str, user_id: str) -> None:
    table_to_search = post_type.value
    
    update_query = f"""
        UPDATE {table_to_search}
        SET deleted_at = NOW()
        WHERE id = %s
        RETURNING author
    """ # if we return the author from this it makes it easier to call

    result = db.write(query_str=update_query, fetch=True, params=(post_id,))
    target_user_id = deep_get(result, 0, 0)

    user_is_admin = is_admin(userid=user_id)

    deletion_reason = f"Admin deleted {post_type}" if user_is_admin else f"User deleted {post_type}"
    modaction = ""
    query_str = """
        INSERT INTO moderation_actions (
            action,
            target_user_id,
            {},
            performed_by,
            reason,
            created_at   
        ) VALUES (%s, %s, %s, %s, %s, NOW())
    """


    match post_type:
        case PostType.MESSAGE:
            modaction = ModerationAction.DELETE_MESSAGE.value
            query_str = query_str.format("target_message_id")
            
        case PostType.POST | PostType.REPLY:
            modaction = ModerationAction.DELETE_POST.value if post_type == PostType.POST else ModerationAction.DELETE_REPLY.value
            query_str = query_str.format("target_post_id")
        case _:
            log.error("Invalid modaction passed: %s", modaction)

    log_action = db.write(query_str=query_str, params=(modaction, target_user_id, post_id, user_id, deletion_reason))

    return None


