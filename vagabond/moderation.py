from vagabond.services import dbmanager as db
from vagabond.utility import deep_get
from vagabond.sessions.module import get_session_id, get_userid_from_session
from flask import abort, redirect, url_for, jsonify

from functools import wraps
from enum import Enum, auto, StrEnum
import logging

log = logging.getLogger(__name__)

class UserPermission(StrEnum):
    USER = "user"               # normal registered user
    MODERATOR = "moderator"     # forum moderator
    ADMIN = "admin"             # site admins who moderate, well..moderators

def get_role_from_userid(userid: str) -> UserPermission | None:

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
        role_to_return = UserPermission(current_role)
    except ValueError as e:
        log.error("Failure converting user role into a UserPermission")
        return None

    return role_to_return

def has_permission(userid: str, roles:list[UserPermission]) -> bool:
    return True if get_role_from_userid(userid) in roles else False

""" Decorator that checks if a user has authentication for a given route, with the new roles system
    @requires_permission([UserPermission.ADMIN, ...])
      Note: It is recomended to alias the user permissions for readability """
def requires_permission(roles: list[UserPermission]):
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

# these actions can also be performed by a special user named "SYSTEM" which is automated
# TODO: move over ban data to another table specifically for it
class ModerationAction(Enum):
    BAN_USER = 'ban_user'
    UNBAN_USER = 'unban_user'
    SHADOWBAN_USER = 'shadowban_user' # i see no upside of adding a "unshadowban" if you have this, you've earned it
    MUTE_USER = 'mute_user'
    DELETE_POST = 'delete_post'
    UNDELETE_POST = 'undelete_post'
    DELETE_REPLY = 'delete_reply' # undeleting a reply also seems kind of useless
    WARN_USER = 'warn_user'
    EDIT_POST = 'edit_post'
    LOCK_POST = 'lock_post'
    PIN_POST = 'pin_post'
    CHANGE_USERNAME = 'change_username'
    ASSIGN_ROLE = 'assign_role'
    UNASSIGN_ROLE = 'unassign_role'
    SUSPEND_USER = 'suspend_user'
    ENABLE_2FA = 'enable_2fa'
    DISABLE_2FA = 'disable_2fa'
    REVERT_ACTION = 'revert_action'


def is_admin(userid: str) -> bool:
    return has_permission(userid=userid, roles=[UserPermission.ADMIN, UserPermission.MODERATOR])

# i dont see any reason to "unhellban someone"
def hellban_user(userid: str, admin_userid: str | None = None, reason: str | None = None) -> None: # interesting way of optional arguments with type checking

    if not userid:
        log.warning("hellban was given a null userid")
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
        admin_userid or 1, # "SYSTEM" user
        reason
    ))

    return None

def soft_delete_user_post(post_type: str, post_id: str, user_id: str) -> None:
    table_to_search = ""
    if post_type == "post": table_to_search = "posts"
    elif post_type == "reply": table_to_search = "replies"
    else:
        log.error("Invalid post type: passed to soft_delete_user_post")
        return None
    
    update_query = f"""
        UPDATE {table_to_search}
        SET deleted_at = NOW()
        WHERE id = %s
        RETURNING author
    """ # if we return the author from this it makes it easier to call

    result = db.write(query_str=update_query, fetch=True, params=(post_id,))
    target_user_id = deep_get(result, 0, 0)

    user_is_admin = is_admin(userid=user_id)

    modaction = ""
    if post_type == "post": modaction = ModerationAction.DELETE_POST.value
    elif post_type == "reply": modaction = ModerationAction.DELETE_REPLY.value

    deletion_reason = ""
    if user_is_admin == True: deletion_reason = f"Admin deleted {post_type}"
    elif user_is_admin == False: deletion_reason = f"User deleted {post_type}"

    # now lets log the action
    log_action = db.write(query_str="""
        INSERT INTO moderation_actions (
            action,
            target_user_id,
            target_post_id,
            performed_by,
            reason,
            created_at   
        ) VALUES (%s, %s, %s, %s, %s, NOW())
    """, params=(modaction, target_user_id, post_id, user_id, deletion_reason))

    return None


