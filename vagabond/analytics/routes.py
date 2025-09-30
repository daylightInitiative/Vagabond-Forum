from vagabond.analytics import analytics_bp
from vagabond.services import dbmanager, limiter
from vagabond.sessions.module import get_session_id, abort_if_not_signed_in, get_userid_from_session
from vagabond.permissions import is_admin
from vagabond.utility import rows_to_dict, deep_get
from flask import abort, redirect, jsonify, request, render_template
import logging

log = logging.getLogger(__name__)

@analytics_bp.route('/get_analytics_data', methods=['GET'])
def send_analytics_data():
    if request.method == "GET":
        abort_if_not_signed_in()

        # admin check
        sid = get_session_id()
        userid = get_userid_from_session(sessionID=sid)
        can_view = is_admin(userid)
        if can_view == False:
            abort(401)

        data_rows, data_cols = dbmanager.read(query_str="""
            SELECT pagePath, hits
            FROM exitPages
            WHERE TRUE
        """, get_columns=True)

        data_dict = rows_to_dict(data_rows, data_cols)

        log.debug(data_dict)

        return jsonify(data_dict), 200
    elif request.method == "POST":
        return '', 401

# since we're google.... we need to use funny terminology lol
@analytics_bp.route('/analytics', methods=['GET', 'POST'])
def acquiesce_exitpage():

    if request.method == "GET":

        abort_if_not_signed_in()

        # admin check
        sid = get_session_id()
        userid = get_userid_from_session(sessionID=sid)
        can_view = is_admin(userid)
        if can_view == False:
            abort(401)

        return render_template("analytics.html")
    elif request.method == "POST":
        # for right now before we get more "advanced" analytics
        # we're just going to track if the user is_online or not.
        analytics_data = request.get_json()
        log.debug(analytics_data)

        exit_page_path = analytics_data.get("exitpage")

        # save exit page data
        dbmanager.write(query_str="""
            INSERT INTO exitPages (pagePath, hits)
            VALUES (%s, 1)
            ON CONFLICT (pagePath)
            DO UPDATE SET hits = exitPages.hits + 1
        """, params=(exit_page_path,)) # in this case hits is ambigious so we reference the value explicitly when reading

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