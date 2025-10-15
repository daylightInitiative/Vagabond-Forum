from vagabond.constants import RouteStatus
from vagabond.sessions.module import (
    redirect_if_already_logged_in,
    create_session, invalidate_session,
    get_session_id, get_fingerprint,
    associate_fingerprint_to_session,
    csrf_exempt
)
from vagabond.utility import get_userid_from_email
from vagabond.login import login_bp
from vagabond.login.module import is_valid_login
from vagabond.moderation import is_admin
from vagabond.services import limiter, dbmanager as db
from flask import request, make_response, redirect, url_for, jsonify, session
from vagabond.flask_wrapper import custom_render_template

import logging

log = logging.getLogger(__name__)

@login_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("70 per minute", methods=["POST"])
@csrf_exempt
def serve_login():

    redirect_if_already_logged_in()

    if request.method == "GET":
        return custom_render_template("login.html")
    elif request.method == "POST":

        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA}), 422
        
        is_authenticated, errmsg = is_valid_login(email=email, password=password)
        
        if is_authenticated:
        
            # lets get the userid
            userid = get_userid_from_email(email=email)
            sid = create_session(userid=userid, request_obj=request)

            if not userid:
                return custom_render_template("login.html", errmsg="Internal server error: Failed to fetch user")    

            if not sid:
                return custom_render_template("login.html", errmsg="Internal server error: Unable to acquire session ID")

            log.debug("Sending session to client")
            response = make_response(redirect(url_for("index")))
            response.set_cookie(key="sessionID", value=sid, max_age=7200, samesite="Strict")

            #session['sessionID'] = sid

            # now that we have set the session id, lets associate this fingerprint with the sid
            # mainly for internal security, but we also use this for analytics

            user_fingerprint = get_fingerprint()
            associate_fingerprint_to_session(fingerprint=user_fingerprint, sessionID=sid)

            return response
        else:
            return custom_render_template("login.html", errormsg=errmsg)

@login_bp.route('/logout', methods=["GET"])
@csrf_exempt
def logout():
    sid = get_session_id()
    if sid:
        invalidate_session(sessionID=sid)

    response = make_response(redirect(url_for('login.serve_login')))
    response.delete_cookie('sessionID')
    #del session['sessionID']
    # i found that i had never deleted the cookie even after signout

    return response
