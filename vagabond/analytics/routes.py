from vagabond.analytics import analytics_bp
from vagabond.services import dbmanager, limiter
from vagabond.sessions.module import get_session_id
from flask import abort, redirect, jsonify, request
import logging

log = logging.getLogger(__name__)

# since we're google.... we need to use funny terminology lol
@analytics_bp.route('/analytics', methods=['POST'])
def acquiesce_exitpage():

    # for right now before we get more "advanced" analytics
    # we're just going to track if the user is_online or not.
    analytics_data = request.get_json()
    log.debug(analytics_data)

    # save exit page data

    #log.debug(get_session_id())
    # if a session is present, update is_online to false
    sid = get_session_id()
    if sid:
        dbmanager.write(query_str="""
            UPDATE users 
            SET is_online = FALSE
            FROM sessions_table st
            WHERE users.id = st.user_id AND sid = %s
        """, params=(sid,))

    return '', 200