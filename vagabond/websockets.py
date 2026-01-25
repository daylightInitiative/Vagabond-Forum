from flask_socketio import ConnectionRefusedError
from vagabond.services import socketio
from vagabond.sessions import get_session_id, get_userid_from_session
from flask_socketio import emit
from flask import request
import logging

log = logging.getLogger(__name__)


# on connect we want them to send the sid cookie
@socketio.on('connect')
def connect_event(auth):
    sid = get_session_id()
    if not sid:
        raise ConnectionRefusedError('Unauthorized: Invalid SessionID')
    log.warning("websocket auth validated")
    emit('my response', {'data': 'Connected'})
    

@socketio.on('disconnect')
def disconnect_event(reason):
    log.debug('Client disconnected, reason:', reason)

@socketio.on('message')
def message_event(json):
    pass


@socketio.on_error()        # Handles the default namespace
def error_handler(e):
    log.error(e)

# @socketio.on_error('/chat') # handles the '/chat' namespace
# def error_handler_chat(e):
#     pass

@socketio.on_error_default  # handles all namespaces without an explicit error handler
def default_error_handler(e):
    log.error(e)