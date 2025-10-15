
from vagabond.services import dbmanager as db
from vagabond.utility import deep_get, is_valid_userid
import logging

log = logging.getLogger(__name__)

def can_add_user_to_group(userID: str, groupID: str) -> bool:
    if not is_valid_userid(userID=userID):
        return False # ignore

    get_is_in_group = db.read(query_str="""
        SELECT EXISTS (
            SELECT 1
            FROM message_group_users
            WHERE user_id = %s AND group_id = %s
        );
    """, params=(userID, groupID,))

    is_in_group_already = deep_get(get_is_in_group, 0, 0)

    if is_in_group_already is None:
        log.warning("Failure to validate if user could join group")
        return False

    if is_in_group_already:
        log.debug("Requested (user_id=%s, group_id=%s) already exists", userID, groupID)
        return False
    
    return True