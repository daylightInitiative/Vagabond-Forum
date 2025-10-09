from vagabond.analytics import analytics_bp
from vagabond.services import dbmanager, limiter
from vagabond.sessions.module import get_session_id, abort_if_not_signed_in, get_userid_from_session, get_fingerprint, csrf_exempt
from vagabond.moderation import is_admin
from vagabond.utility import rows_to_dict, deep_get
from flask import abort, redirect, jsonify, request
from vagabond.flask_wrapper import custom_render_template
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

        exit_pages_dict_array = rows_to_dict(data_rows, data_cols)

        # GET COUNT OF ALL USERS THAT ARE UNREGISTERED
        # GET COUNT OF ALL USERS THAT ARE REGISTERED
        # instead of finding it positively we handle it negatively by selecting 1
        reg_rows, reg_cols = dbmanager.read(query_str="""
            SELECT
                (SELECT COUNT(*) FROM users) AS num_registered,
                (
                    SELECT COUNT(*) as num_unregistered
                    FROM impressions imp
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM sessions_table st
                        WHERE st.fingerprint_id = imp.impression_hash
                    )
                )
        """, get_columns=True)
        # get unregistered users by saying IF FINGERPRINT ISNT IN SESSION IDS THEN (not a user)

        registry_data = rows_to_dict(reg_rows, reg_cols)[0]

        # need to combine registry data with the dict inside exit_pages_dict_array
        data_dict = {
            "exit_pages": exit_pages_dict_array,
            "registry_data": registry_data
        }

        return jsonify(data_dict), 200
    elif request.method == "POST":
        return '', 401

# since we're google.... we need to use funny terminology lol
@analytics_bp.route('/analytics', methods=['GET', 'POST'])
@csrf_exempt
def acquiesce_exitpage():

    if request.method == "GET":

        abort_if_not_signed_in()

        # admin check
        sid = get_session_id()
        userid = get_userid_from_session(sessionID=sid)
        can_view = is_admin(userid)
        if can_view == False:
            abort(401)

        return custom_render_template("analytics.html")
    elif request.method == "POST":
        # for right now before we get more "advanced" analytics
        # we're just going to track if the user is_online or not.
        analytics_data = request.get_json()

        exit_page_path = analytics_data.get("exitpage")

        # save exit page data
        dbmanager.write(query_str="""
            INSERT INTO exitPages (pagePath, hits)
            VALUES (%s, 1)
            ON CONFLICT (pagePath)
            DO UPDATE SET hits = exitPages.hits + 1
        """, params=(exit_page_path,)) # in this case hits is ambigious so we reference the value explicitly when reading

        # update the duration for a session end
        user_fingerprint = get_fingerprint()
        dbmanager.write(query_str="""
            UPDATE impression_durations
            SET impression_end = NOW()
            WHERE id = (
                SELECT id
                FROM impression_durations
                WHERE impression_hash = %s
                AND impression_end IS NULL
                ORDER BY impression_start DESC LIMIT 1
            );
        """, params=(user_fingerprint,)) # before updating get the latest start and limit it by 1 for performance

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

        log.warning("Saved analytics data for viewing of SID: %s", sid)

        return '', 200