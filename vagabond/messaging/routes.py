
# instead of hardcoding a route, lets create a messaging api that requires authentication

import json
from vagabond.moderation import soft_delete_user_post
from vagabond.sessions.module import (
    get_session_id, get_userid_from_session, is_user_logged_in, csrf_exempt
)
from vagabond.messaging import messaging_bp
from vagabond.messaging.module import can_user_access_group, is_user_in_group, is_user_message_owner
from flask import abort, jsonify, request, redirect
from vagabond.constants import MESSAGE_PAGE_LIMIT, ModerationAction, PostType, RouteStatus
from vagabond.services import dbmanager as db
from vagabond.utility import deep_get, get_group_owner, is_valid_userid, rows_to_dict
import logging

log = logging.getLogger(__name__)


# change group owner, delete group
@messaging_bp.route("/api/v1/messages/groups/<group_id>", methods=["PATCH", "DELETE"])
def serve_group(group_id):

    if not is_user_logged_in():
        return jsonify({"error": RouteStatus.INVALID_PERMISSIONS}), 401

    
    sid = get_session_id()
    userID = get_userid_from_session(sessionID=sid)

    if not can_user_access_group(userID=userID, groupID=group_id):
        return jsonify({"error": RouteStatus.INVALID_PERMISSIONS.value}), 401

    if request.method == "PATCH":

        data = request.get_json()

        new_owner = data.get("new_owner")
        if not new_owner or not is_valid_userid(userID=new_owner):
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA}), 422

        # change the group owner only if the invoker is already equal to the owner
        group_owner = get_group_owner(groupID=group_id)

        if not group_owner:
            log.error("Group of id: %s does not have an owner.", group_id)
            return jsonify({"error": RouteStatus.INTERNAL_SERVER_ERROR}), 500
        
        if userID != group_owner:
            return jsonify({"error": RouteStatus.INVALID_PERMISSIONS}), 401
        
        db.write(query_str="""
            UPDATE message_recipient_group
                SET group_owner = %s
            WHERE groupid = %s
            ORDER BY added_at DESC
        """, params=(new_owner, group_id,))

    elif request.method == "DELETE":

        group_owner = get_group_owner(groupID=group_id)

        if group_owner != userID:
            return jsonify({"error": RouteStatus.INVALID_PERMISSIONS}), 401
        
        db.write(query_str="""
            UPDATE message_recipient_group
                SET deleted_at = NOW()
            WHERE groupid = %s
        """, params=(group_id,))

        # add to audit log this action,
        modaction = ModerationAction.DELETE_GROUP
        query_str = """
            INSERT INTO moderation_actions (
                action,
                target_user_id,
                target_group_id,
                performed_by,
                reason,
                created_at   
            ) VALUES (%s, %s, %s, %s, %s, NOW())
        """

        log_action = db.write(query_str=query_str, params=(modaction, userID, group_id, userID, "User deleted group"))

    return '', 200


# when getting the paginated output we should filter by date ASC
# for getting paginated output, creating a new message returning the postid for the javascript (that way its easier to reply to it)
@messaging_bp.route("/api/v1/messages/groups/<group_id>/messages", methods=["GET", "POST"])
def serve_messages(group_id):

    if not is_user_logged_in():
        return jsonify({"error": RouteStatus.INVALID_PERMISSIONS}), 401

    
    sid = get_session_id()
    userID = get_userid_from_session(sessionID=sid)

    if not can_user_access_group(userID=userID, groupID=group_id):
        return jsonify({"error": RouteStatus.INVALID_PERMISSIONS.value}), 401

    data = request.get_json()

    if request.method == "GET":
        
        page_offset = data.get("page_offset")
        if not isinstance(page_offset, int) and page_offset >= 1:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 422

        # get the page index for our pagination
        param_dict = {
            "message_page_limit": MESSAGE_PAGE_LIMIT,
            "message_group_id": group_id,
            "page_offset": ((page_offset - 1) * MESSAGE_PAGE_LIMIT) # note to frontend: starts at index 1
        }
        get_rows, get_cols = db.read(query_str="""
            SELECT *
            FROM user_messages
            WHERE msg_group_id = %(message_group_id)s AND deleted_at IS NULL
            ORDER BY creation_date DESC
            LIMIT %(message_page_limit)s OFFSET %(page_offset)s
        """, get_columns=True, params=param_dict)

        paginated_messages_dict = rows_to_dict(get_rows, get_cols)

        log.debug(paginated_messages_dict)
        return jsonify(paginated_messages_dict), 200

    elif request.method == "POST":
        # creation of a new message

        msg_contents = data.get("contents")

        if not msg_contents:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 422

        msg_group_id = group_id

        if not msg_group_id:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 422

        msg_creator_id = userID

        if not can_user_access_group(userID=msg_creator_id, groupID=msg_group_id):
            log.warning("(user_id=%s, group_id=%s) cannot access group upon creating message", msg_creator_id, msg_group_id)
            return jsonify({"error": RouteStatus.INVALID_PERMISSIONS.value}), 401
        
        db.write(query_str="""
            INSERT INTO user_messages (contents, author, msg_group_id)
                 VALUES (%s, %s, %s)
        """, params=(msg_contents, msg_creator_id, msg_group_id,))

        # update the last message timestamp
        db.write(query_str="""
            UPDATE message_recipient_group
            SET last_message = NOW()
            WHERE groupid = %s
        """, params=(group_id,))

        log.debug("created new message in (user_id=%s, group_id=%s)", msg_creator_id, msg_group_id)

        return '', 200


# for deleting and editing messages of a particular group id,
@messaging_bp.route("/api/v1/messages/groups/<group_id>/messages/<message_id>", methods=["PATCH", "DELETE"])
def serve_edit_message(group_id, message_id):

    if not is_user_logged_in():
        return jsonify({"error": RouteStatus.INVALID_PERMISSIONS}), 401

    sid = get_session_id()
    userID = get_userid_from_session(sessionID=sid)

    

    if not can_user_access_group(userID=userID, groupID=group_id):
        return jsonify({"error": RouteStatus.INVALID_PERMISSIONS.value}), 401

    if request.method == "PATCH":
        data = request.get_json()
        new_contents = data.get("edited_message")
        if not new_contents:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 422

        if not is_user_message_owner(userID=userID, messageID=message_id):
            log.warning("User %s tried to modify an existing message that was not owned by them")
            return jsonify({"error": RouteStatus.INVALID_PERMISSIONS.value}), 401

        # before we edit, lets take a shadow log of all edits
        db.write(query_str="""
            INSERT INTO edited_messages (original_contents, message_id)
            SELECT contents, id
            FROM user_messages
            WHERE id = %s AND msg_group_id = %s
        """, params=(message_id, group_id,))

        # edit the message of this message id
        db.write(query_str="""
            UPDATE user_messages
            SET contents = %s
            WHERE id = %s AND msg_group_id = %s
        """, params=(new_contents, message_id, group_id,))

        log.debug("edited message (message_id=%s, group_id=%s)", message_id, group_id)

    elif request.method == "DELETE":
        
        log.debug("Deleting message of id: %s", message_id)

        soft_delete_user_post(PostType.MESSAGE, message_id, userID)




    return '', 200

# its critical we dont really delete messages for later investigation, etc.
@messaging_bp.route("/api/v1/messages/groups/create", methods=["POST"])
def serve_create_group():
    
    if not is_user_logged_in():
        return jsonify({"error": RouteStatus.INVALID_PERMISSIONS}), 401

    data = request.get_json()
    sid = get_session_id()
    userID = get_userid_from_session(sessionID=sid)

    if request.method == "POST":
        # create a new group
        # get the userid we are trying to message, its a json list
        users_to_add = data.get("recipient_list")
        if not users_to_add or len(users_to_add) <= 0:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 422

        log.debug(users_to_add)

        # create group, return its id
        get_group_id = db.write(query_str="""
            INSERT INTO message_recipient_group
                DEFAULT VALUES
            RETURNING groupid
        """, fetch=True)
        group_id = deep_get(get_group_id, 0, 0) or -1
        if group_id < 0:
            log.error("Failure to create message group")
            return jsonify({"error": RouteStatus.INTERNAL_SERVER_ERROR.value}), 500
        
        log.debug(f"created group_id={group_id}")

        # now that we have the groupid, lets create the group users table and add each user

        for user_id in users_to_add:
            log.debug(f"creating entry to group_users, (group_id={group_id}, user_id={user_id})")
            db.write(query_str="""
                INSERT INTO message_group_users (group_id, user_id)
                    VALUES (%s, %s)
            """, params=(group_id, user_id,))
                


        return '', 200


# send messages
# create message group
# receieve messages paginated, into the scroll
