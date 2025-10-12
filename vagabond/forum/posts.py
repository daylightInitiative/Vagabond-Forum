from vagabond.services import dbmanager, limiter
from vagabond.utility import rows_to_dict, deep_get, title_to_content_hint
from vagabond.dbmanager import DBStatus
from vagabond.queries import *
from vagabond.sessions.module import (
    abort_if_not_signed_in,
    get_session_id,
    get_userid_from_session,
    is_user_logged_in,
    get_tsid
)
from vagabond.forum.module import get_is_category_locked
from vagabond.moderation import is_admin
from vagabond.forum import forum_bp
from vagabond.constants import *
from flask import request, redirect, abort, url_for, jsonify
from vagabond.flask_wrapper import custom_render_template
import logging

log = logging.getLogger(__name__)

# this file is for post specific functions and deletion of them

# save post draft route
@forum_bp.route("/save_draft", methods=["POST", "GET"])
@limiter.limit("50 per minute", methods=["POST"])
@limiter.limit("50 per minute", methods=["GET"])
def save_draft():
    
    sid = get_session_id()
    if not is_user_logged_in():
        abort(401)

    if request.method == "GET":
        # get saved draft logic here
        
        temp_session_id = get_tsid(sessionID=sid)
        
        get_draft = dbmanager.read(query_str="""
            SELECT draft_text
            FROM temp_session_data
            WHERE tempid = %s and LENGTH(draft_text) > 0
        """, params=(temp_session_id,))

        saved_draft_text = deep_get(get_draft, 0, 0)

        if not saved_draft_text:
            return jsonify({"error": RouteError.FETCH_NO_CONTENT}), 204 # no content
        
        draft = {
            "contents": saved_draft_text
        }

        return jsonify(draft), 200



    elif request.method == "POST":
        data = request.get_json()
        log.debug(data)

        # get the temporary data id
        tsid = get_tsid(sessionID=sid)

        text_to_save = data.get("contents")
        save_draft = dbmanager.write(query_str="""
            UPDATE temp_session_data
            SET draft_text = %s
            WHERE tempid = %s
        """, params=(text_to_save, tsid,))

        if save_draft == DBStatus.FAILURE:
            log.critical("Failed to save draft data for tsid: %s", tsid)
            return jsonify({"error": RouteError.INTERNAL_SERVER_ERROR}), 500

    return '', 200

# for posting we can just reuse this route
@forum_bp.route('/post', methods=['GET', 'POST'])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("70 per minute", methods=["POST"])
def submit_new_post():

    abort_if_not_signed_in()

    sessionID = get_session_id()
    author = get_userid_from_session(sessionID=sessionID)
    category_id = request.args.get('category')

    if request.method == "GET":
        
        if not category_id:
            return jsonify({"error": RouteError.INVALID_CATEGORY_ID}), 422
        
        category_locked = get_is_category_locked(categoryID=category_id)

        if category_locked and not is_admin(userid=author):
            abort(401)

        return custom_render_template("create_post.html", post_category=category_id)

    elif request.method == "POST":

        category_locked = get_is_category_locked(categoryID=category_id)

        if category_locked and not is_admin(userid=author):
            abort(401)

        title = request.form.get('title', type=str)
        description = request.form.get('description', type=str)
        
        if not title or not description:
            return jsonify({"error": RouteError.INVALID_FORM_DATA}), 400
        
        category_id = request.args.get('category')
        if not category_id:
            return jsonify({"error": RouteError.INVALID_CATEGORY_ID}), 422

        # now, instead of having to create this every time, lets save it to the db (auto truncates)
        url_safe_title = title_to_content_hint(title)

        retrieved = dbmanager.write(query_str="INSERT INTO posts (title, contents, author, url_title, category_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            fetch=True,
            params=(title, description, author, url_safe_title, category_id,)
        )

        new_post_id = deep_get(retrieved, 0, 0)
        log.debug(new_post_id)
        if new_post_id:
            return redirect(url_for("forum.serve_post_by_id", post_num=new_post_id, content_hint=url_safe_title))

    return jsonify({"error": RouteError.INTERNAL_SERVER_ERROR}), 500