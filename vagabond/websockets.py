from flask_socketio import ConnectionRefusedError, disconnect, join_room, send
from vagabond.constants import RouteError
from vagabond.flask_wrapper import error_response
from vagabond.messaging.module import is_user_in_group
from vagabond.services import socketio
from vagabond.sessions import get_session_id, get_userid_from_session
from flask_socketio import emit
from flask import request
import logging

from vagabond.sessions.module import is_valid_session

log = logging.getLogger(__name__)


# on connect we want them to send the sid cookie
@socketio.on('connect')
def connect_event(auth):
    sid = get_session_id()
    if not sid and is_valid_session(sessionID=sid):
        raise ConnectionRefusedError('Unauthorized: Invalid SessionID')
    log.warning("websocket auth validated")
    # emit('my response', {'data': 'Connected'})
    

@socketio.on('disconnect')
def disconnect_event(reason):
    log.debug('Client disconnected, reason: %s', reason)

# generic "message" event handler
@socketio.on('message')
def message_event(json):
    pass

def get_user_and_group(json):
    sid = get_session_id()
    if not sid or not is_valid_session(sessionID=sid):
        disconnect(request.sid)
        raise RouteError.INVALID_SESSION

    userID = get_userid_from_session(sessionID=sid)

    if not json:
        raise RouteError.INVALID_FORM_DATA

    groupID = json.get("groupID")
    if not groupID:
        raise RouteError.INVALID_FORM_DATA

    if not is_user_in_group(userID=userID, groupID=groupID):
        disconnect(request.sid)
        raise RouteError.INVALID_PERMISSIONS

    return userID, groupID

# we dont do this in connect because we need to send data
@socketio.on('join')
def join_room_event(json):
    userID, groupID = get_user_and_group(json=json)
    join_room(groupID, request.sid)
    log.debug("%s joined the group", userID)

# acts simply as a ping for all the messages to refresh
@socketio.on('new_message')
def new_message_event(json):
    userID, groupID = get_user_and_group(json=json)
    
    # now we can broadcast to everyone else in the room
    sid_to_skip = request.sid  # senders sid
    log.debug("echoing to everyone in the group except the sender")
    emit("new_message", json, broadcast=True, skip_sid=sid_to_skip, to=groupID)
    

@socketio.on_error()        # Handles the default namespace
def error_handler(e):
    log.error(e)

# @socketio.on_error('/chat') # handles the '/chat' namespace
# def error_handler_chat(e):
#     pass

@socketio.on_error_default  # handles all namespaces without an explicit error handler
def default_error_handler(e):
    log.error(e)