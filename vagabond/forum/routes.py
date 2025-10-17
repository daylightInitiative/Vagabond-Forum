from vagabond.services import dbmanager as db, limiter
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
from vagabond.forum.module import get_is_post_locked, is_user_content_owner, get_is_category_locked, get_is_post_deleted
from vagabond.moderation import is_admin, soft_delete_user_post
from vagabond.forum import forum_bp
from vagabond.constants import *
from flask import request, redirect, abort, url_for, jsonify
import logging

from vagabond.flask_wrapper import custom_render_template

log = logging.getLogger(__name__)

# view post route
@forum_bp.route("/forums/<int:post_num>/", defaults={'content_hint': None}, methods=["GET"])
@forum_bp.route("/forums/<int:post_num>/<content_hint>", methods=["GET", "POST"])
@limiter.limit("125 per minute", methods=["GET", "POST"])
def serve_post_by_id(post_num, content_hint):
    if request.method == "GET":
        log.debug("We are viewing a singular post from /forums/%s/%s", post_num, content_hint)

        sid = get_session_id()
        user_id = get_userid_from_session(sessionID=sid)

        # get the content hint, if the content hint doesnt match, redirect early.
        view_single, column_names = db.read(query_str=VIEW_POST_BY_ID, fetch=True, get_columns=True, params=(post_num,))
        get_post = rows_to_dict(view_single, column_names)
        single_post = deep_get(get_post, 0)

        log.debug(single_post)

        saved_content_hint = single_post.get("url_title")

        if not content_hint or content_hint != saved_content_hint:
            print("Theres no content hint, redirect")
            return redirect( url_for("forum.serve_post_by_id", post_num=post_num, content_hint=saved_content_hint) )

        db.write(query_str='UPDATE posts SET views = views + 1 WHERE id = %s;',
            params=(post_num,))

        # get all the posts replies
        replies_rows, column_names = db.read(query_str=QUERY_PAGE_REPLIES, get_columns=True, params=(post_num, user_id,))
        replies_list = rows_to_dict(replies_rows, column_names)

        log.debug(replies_list)

        # get if the post is locked or not
        is_post_locked = get_is_post_locked(post_num=post_num)

        is_post_owner = is_user_content_owner(post_type="post", userid=user_id, postid=post_num)
        is_reply_owner = is_user_content_owner(post_type="reply", userid=user_id, postid=post_num)

        is_post_deleted = get_is_post_deleted(post_num=post_num)

        return custom_render_template("view_post.html", post=single_post, replies=replies_list, is_post_locked=is_post_locked, is_post_owner=is_post_owner, is_post_deleted=is_post_deleted, is_reply_owner=is_reply_owner)

    elif request.method == "POST" and request.form.get("_post_type") and request.form.get("_method") == "DELETE":
        # hacky way of deleting with just html forms, i'll bloat it up with proper javascript later
        abort_if_not_signed_in()
        
        post_type = request.form.get('_post_type')

        if not post_type:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 400
        
        # decide if the user is the post owner by the session
        sid = get_session_id()
        user_id = get_userid_from_session(sessionID=sid)

        log.debug(post_type)

        if post_type == "post":
            post_id = request.form.get('post_id')

            if not post_id:
                return jsonify({"error": RouteStatus.INVALID_POST_ID.value}), 422

            is_owner = is_user_content_owner(post_type=post_type, userid=user_id, postid=post_id)

            if not is_owner and is_admin(userid=user_id) == False:
                return abort(401)
            
            # set the post as soft deleted
            soft_delete_user_post(PostType.POST, post_id=post_id, user_id=user_id)

            log.debug("Post has been soft marked for deletion")
            return redirect(url_for("index"))
        elif post_type == "reply":
            reply_id = request.form.get('reply_id')

            is_owner = is_user_content_owner(post_type=post_type, userid=user_id, postid=reply_id) or is_admin(userid=user_id)

            if not is_owner:
                return abort(401)

            if not reply_id:
                return jsonify({"error": RouteStatus.INVALID_POST_ID.value}), 422
            
            soft_delete_user_post(post_type=PostType.REPLY, post_id=reply_id, user_id=user_id)

            log.info("Reply has been soft marked for deletion")

            return redirect(url_for("forum.serve_post_by_id", post_num=post_num, content_hint=content_hint))

    elif request.method == "POST":
        abort_if_not_signed_in()

        is_post_locked = get_is_post_locked(post_num)
        if is_post_locked:
            return abort(401)

        # for replies we get the data, and save it nothing more
        post_id = request.form.get('post_id') # hacky way of saving the postid
        reply = request.form.get('reply')

        # minimum of 20 characters in a reply
        # (we can detect spamming later)
        if not post_id or len(reply) <= 5:
            return '<p>Post is too short or invalid post id</p>', 400
        
        sessionID = get_session_id() #guarenteed because of the abort
        author = get_userid_from_session(sessionID=sessionID)

        log.debug("creating a reply linked to the parent post")
        db.write(query_str="INSERT INTO replies (parent_post_id, contents, author) VALUES (%s, %s, %s)",
            params=(post_id, reply, author))

        # redirect back to the view_forum to trigger the refresh
        return redirect(url_for("forum.serve_post_by_id", post_num=post_id, content_hint=content_hint))


@forum_bp.route("/forums", methods=["GET", "POST", "PATCH"])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("80 per minute", methods=["POST"])
def serve_forum():


    if request.method == "GET":

        page_num = request.args.get('page')
        category_id = request.args.get('category')

        if not page_num:
            return jsonify({"error": RouteStatus.INVALID_PAGE_ID.value}), 422
        
        if not category_id:
            return jsonify({"error": RouteStatus.INVALID_CATEGORY_ID.value}), 422
        
        log.debug(f"queried post {page_num}")
        try:
            page_num = int(page_num)
            if page_num <= 0:
                raise ValueError("Invalid page number")
        except (TypeError, ValueError):
            # redirect to the first page if page_num is invalid (postgres id starts at 1)
            return redirect(url_for("index"))

        page_offset = str((page_num - 1) * FORUM_PAGE_LIMIT)

        # query the response as json, page the query, include nested replies table

        # instead of positional arguments, we're going to used named ones for this
        # since theres so many reuses of the current user viewing the post
        sid = get_session_id()
        userid = get_userid_from_session(sessionID=sid)

        named_params = {
            "current_userid": userid,
            "category_id": category_id,
            "page_limit": str(FORUM_PAGE_LIMIT),
            "page_offset": page_offset
        }

        post_rows, column_names = db.read(query_str=QUERY_PAGE_POSTS, get_columns=True, params=named_params)
        posts = rows_to_dict(post_rows, column_names)

        log.debug(posts)
        category_locked = get_is_category_locked(categoryID=category_id)

        return custom_render_template("forums.html", posts=posts, forum_category_id=category_id, forum_category_locked=category_locked)

