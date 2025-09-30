from vagabond.services import dbmanager, limiter
from vagabond.utility import rows_to_dict, deep_get, title_to_content_hint
from vagabond.dbmanager import DBStatus
from vagabond.queries import *
from vagabond.sessions.module import (
    abort_if_not_signed_in,
    get_session_id,
    get_userid_from_session,
    is_user_logged_in,
    get_tdid
)
from vagabond.forum.module import get_is_post_locked
from vagabond.permissions import is_admin
from vagabond.forum import forum_bp
from vagabond.constants import *
from flask import request, redirect, abort, url_for, render_template, jsonify
import logging

log = logging.getLogger(__name__)

# view post route
@forum_bp.route("/forums/<int:post_num>/<content_hint>", methods=["GET", "POST"])
@limiter.limit("125 per minute", methods=["GET", "POST"])
def serve_post_by_id(post_num, content_hint):
    if request.method == "GET":
        log.debug("We are viewing a singular post from /forums/%s/%s", post_num, content_hint)

        # get the content hint, if the content hint doesnt match, redirect early.
        view_single, column_names = dbmanager.read(query_str=VIEW_POST_BY_ID, fetch=True, get_columns=True, params=(post_num,))
        get_post = rows_to_dict(view_single, column_names)
        single_post = deep_get(get_post, 0)

        log.debug(single_post)

        saved_content_hint = single_post.get("url_title")

        if content_hint != saved_content_hint:
            print("Theres no content hint, redirect")
            return redirect( url_for("forum.serve_post_by_id", post_num=post_num, content_hint=saved_content_hint) )

        dbmanager.write(query_str='UPDATE posts SET views = views + 1 WHERE id = %s;',
            params=(post_num,))

        # get all the posts replies
        replies_rows, column_names = dbmanager.read(query_str=QUERY_PAGE_REPLIES, get_columns=True, params=(post_num,))
        replies_list = rows_to_dict(replies_rows, column_names)

        log.debug(replies_list)

        # get if the post is locked or not
        is_post_locked = get_is_post_locked(post_num=post_num)

        return render_template("view_post.html", post=single_post, replies=replies_list, is_post_locked=is_post_locked)

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
        dbmanager.write(query_str="INSERT INTO replies (parent_post_id, contents, author) VALUES (%s, %s, %s)",
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

        if not page_num or not category_id:
            return jsonify({"error": "Must supply category and page as URL parameters"}), 422
        
        log.debug(f"queried post {page_num}")
        try:
            page_num = int(page_num)
            if page_num <= 0:
                raise ValueError("Invalid page number")
        except (TypeError, ValueError):
            # redirect to the first page if page_num is invalid (postgres id starts at 1)
            return redirect(url_for("forum.forums.html") + "?page=1")

        page_offset = str((page_num - 1) * PAGE_LIMIT)
        log.debug("is the page offset")

        # query the response as json, page the query, include nested replies table
        post_rows, column_names = dbmanager.read(query_str=QUERY_PAGE_POSTS, get_columns=True, params=(category_id, str(PAGE_LIMIT), page_offset, category_id,))
        posts = rows_to_dict(post_rows, column_names)

        log.debug(posts)


    elif request.method == "POST" and request.form.get("_method") == "DELETE":
        reply_id = request.form.get('post_id')
        abort_if_not_signed_in()

        user_id = get_userid_from_session(sessionID=get_session_id())
        if not is_admin(user_id):
            return jsonify({"error": "Unauthorized"}), 401

        if not reply_id:
            return jsonify({"error": "Invalid post ID"}), 422
        
        get_parent_post_id = dbmanager.write(query_str="""
            UPDATE replies
            SET deleted_at = NOW()
            WHERE id = %s
            RETURNING parent_post_id
        """, fetch=True, params=(reply_id))
        parent_post_id = deep_get(get_parent_post_id, 0, 0)

        log.info("marked reply for deletion")
        return redirect(url_for("forum.serve_post_by_id", post_id=parent_post_id))

    return render_template("forums.html", posts=posts, forum_category_id=category_id)

