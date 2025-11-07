
from vagabond.services import dbmanager as db
from vagabond.utility import deep_get, is_valid_userid
import logging

log = logging.getLogger(__name__)

def get_groups_for_userid(userID: str, groupID: str):
    
    get_groups_by_id = db.read(query_str="""
        SELECT DISTINCT group_id FROM message_group_users
        WHERE user_id = %s AND group_id = %s
    """, params=(userID, groupID,))

    available_groups = deep_get(get_groups_by_id, 0)
    log.debug(available_groups)

    return available_groups



def is_user_in_group(userID: str, groupID: str) -> bool:
    if not is_valid_userid(userID=userID):
        log.warning("is_user_in_group passed an invalid userid: %s", userID)
        return False

    get_is_in_group = db.read(query_str="""
        SELECT EXISTS (
            SELECT 1
            FROM message_group_users
            WHERE user_id = %s AND group_id = %s
        );
    """, params=(userID, groupID,))

    is_in_group_already = deep_get(get_is_in_group, 0, 0)

    if is_in_group_already is None:
        log.warning("Failure to validate if user is in group")
        return True

    if is_in_group_already:
        log.debug("Requested (user_id=%s, group_id=%s) already exists in group", userID, groupID)
        return True
    
    return False

def is_user_message_owner(userID: str, messageID: str) -> bool:
    if not is_valid_userid(userID=userID):
        return False

    is_user_msg_owner = db.read(query_str="""
        SELECT 1
        FROM user_messages
        WHERE id = %s AND author = %s
    """, params=(messageID, userID,))

    is_user_owner = deep_get(is_user_msg_owner, 0, 0) or False
    return is_user_owner

def can_user_access_group(userID: str, groupID: str) -> bool:
    is_in_group = is_user_in_group(userID=userID, groupID=groupID)
    if is_in_group:
        return True
    
    return False
