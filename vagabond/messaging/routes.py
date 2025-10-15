
# instead of hardcoding a route, lets create a messaging api that requires authentication

from vagabond.sessions.module import (
    get_session_id, get_userid_from_session, is_user_logged_in, csrf_exempt
)
from vagabond.messaging import messaging_bp
from vagabond.messaging.module import can_add_user_to_group
from flask import abort, jsonify, request, redirect
from vagabond.constants import RouteStatus
from vagabond.services import dbmanager as db
from vagabond.utility import deep_get
import logging

log = logging.getLogger(__name__)


# change group owner, delete group
@messaging_bp.route("/api/v1/messages/groups/<group_id>", methods=["PATCH", "DELETE"])
def serve_group():
    pass

# when getting the paginated output we should filter by date ASC
# for getting paginated output, creating a new message returning the postid for the javascript (that way its easier to reply to it)
@messaging_bp.route("/api/v1/messages/groups/<group_id>/messages", methods=["GET", "POST"])
def serve_messages():
    pass

# for deleting and editing messages of a particular group id,
@messaging_bp.route("/api/v1/messages/groups/<group_id>/messages/<message_id>", methods=["PATCH", "DELETE"])
def serve_edit_message():
    pass

# its critical we dont really delete messages for later investigation, etc.
@messaging_bp.route("/api/v1/messages/groups/create", methods=["POST"])
@csrf_exempt
def serve_create_group():
    
    # if not is_user_logged_in():
    #     return jsonify({"error": RouteError.INVALID_PERMISSIONS}), 401

    data = request.get_json()

    if request.method == "POST":
        # create a new group
        # get the userid we are trying to message, its a json list
        users_to_add = data.get("recipient_list")
        if not users_to_add or len(users_to_add) <= 0:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA}), 422

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
            return jsonify({"error": RouteStatus.INTERNAL_SERVER_ERROR}), 500
        
        log.debug(f"created group_id={group_id}")

        # now that we have the groupid, lets create the group users table and add each user

        for user_id in users_to_add:
            log.debug(f"creating entry to group_users, (group_id={group_id}, user_id={user_id})")
            can_add_user = can_add_user_to_group(userID=str(user_id), groupID=group_id)
            if can_add_user:
                db.write(query_str=f"""
                    INSERT INTO message_group_users (group_id, user_id)
                        VALUES (%s, %s)
                """, params=(group_id, user_id,))


        return '', 200


# send messages
# create message group
# receieve messages paginated, into the scroll
