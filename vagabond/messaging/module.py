
from vagabond.profile.module import get_profile_info
from vagabond.services import dbmanager as db
from vagabond.utility import deep_get, deep_get_as_type, get_username_from_userid, is_valid_userid, rows_to_dict
import logging

log = logging.getLogger(__name__)


def get_groups_for_userid(userID: str):
    
    # weird postgres rule, but everything with select distinct must be included at the top, but since we only want the group id
    # we put it in a sub query
    get_groups_by_id = db.read(query_str="""
        SELECT DISTINCT group_id
        FROM (
            SELECT u.group_id, g.last_message
            FROM message_group_users AS u
            LEFT JOIN message_recipient_group g ON g.groupid = u.group_id
            WHERE user_id = %s
            ORDER BY g.last_message DESC
        ) AS ordered_groups;
    """, params=(userID,))
    # actually so clever to order by last  message here, forgot i did that
    log.debug("(user=%s, available gids=%s)", userID, get_groups_by_id)

    available_groups = []
    for entry in get_groups_by_id:
        groupID = entry[0]
        available_groups.append(groupID)

    return available_groups

def get_group_type(groupID: str) -> bool:
    
    get_group_type = db.read(query_str="""
        SELECT group_type
        FROM message_recipient_group
        WHERE groupid = %s
    """, params=(groupID))

    gt = deep_get_as_type(get_group_type, str, 0)
    return gt

def get_contacts_from_gids(gids: list):
    # we need to get profile information in one big query using subqueries

    #  make sure to add a LIMIT to this, otherwise it should be fine getting all what we're given! ^q^
    contacts_list = []
    for groupid in gids:

        # # I feel like doing it this wya is OK, since we dont know when we are offline when or how things will change, and will only be loaded once likely
        # group_type = get_group_type(groupID=groupid)
        rows, cols= db.read(query_str="""
            SELECT *
            FROM message_recipient_group
            WHERE groupid = %s
        """, get_columns=True, params=(str(groupid))) # be careful when putting in mismatched types into params

        # now convert it into a dictionary
        get_info = rows_to_dict(rows=rows, columns=cols)
        group_dict = deep_get(get_info, 0)
        
        contacts_list.append(group_dict)

    return contacts_list

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
    
    return is_in_group
