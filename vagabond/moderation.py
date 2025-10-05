from vagabond.services import dbmanager
from vagabond.utility import deep_get

from enum import Enum, auto
import logging

log = logging.getLogger(__name__)

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
    REVERT_ACTION = 'revert_action'


def is_admin(userid: str) -> bool:
    get_is_superuser = dbmanager.read(query_str="""
        SELECT is_superuser
        FROM users
        WHERE id = %s
    """, fetch=True, params=(userid,))
    return deep_get(get_is_superuser, 0, 0) or False

# i dont see any reason to "unhellban someone"
def hellban_user(userid: str, admin_userid: str | None = None, reason: str | None = None) -> None: # interesting way of optional arguments with type checking

    if not userid:
        log.warning("hellban was given a null userid")
        return None

    # hellban user
    dbmanager.write(query_str="""
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

    dbmanager.write(query_str="""
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
    log.debug(update_query)
    log.debug(post_id)

    result = dbmanager.write(query_str=update_query, fetch=True, params=(post_id,))
    log.debug(result)
    target_user_id = deep_get(result, 0, 0)

    user_is_admin = is_admin(userid=user_id)

    modaction = ""
    if post_type == "post": modaction = ModerationAction.DELETE_POST.value
    elif post_type == "reply": modaction = ModerationAction.DELETE_REPLY.value

    deletion_reason = ""
    if user_is_admin == True: deletion_reason = f"Admin deleted {post_type}"
    elif user_is_admin == False: deletion_reason = f"User deleted {post_type}"

    # now lets log the action
    log_action = dbmanager.write(query_str="""
        INSERT INTO moderation_actions (
            action,
            target_user_id,
            target_post_id,
            performed_by,
            reason,
            created_at   
        ) VALUES (%s, %s, %s, %s, %s, NOW())
    """, params=(modaction, target_user_id, post_id, user_id, deletion_reason))


