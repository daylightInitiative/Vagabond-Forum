from vagabond.constants import RouteStatus
from vagabond.email import confirm_2FA_code, generate_2FA_code, generate_token, is_2fa_enabled, send_2auth_login_code, send_2fa_code, send_signup_code
from vagabond.sessions.module import (
    get_auth_user_response,
    redirect_if_already_logged_in,
    create_session, invalidate_session,
    get_session_id, get_fingerprint,
    associate_fingerprint_to_session,
    csrf_exempt
)
from vagabond.utility import get_censored_email, get_userid_from_email
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
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 422
        
        is_authenticated, errmsg = is_valid_login(email=email, password=password)
        
        if is_authenticated:
        
            # lets get the userid
            userid = get_userid_from_email(email=email)

            # check for 2auth
            if is_2fa_enabled(userID=userid):

                #instead of using 2fa codes tied to accounts, we need to just use a stateless email verification link
                #for something as important as login
                email_token = generate_token(email=email)
                send_2auth_login_code(email=email, code=email_token)

                censored_email = get_censored_email(email)

                return custom_render_template("confirm_email.html", text="""
                    A temporary 2FA code has been sent to your email, as 2FA authentication has been enabled on this account. The link will expire in one hour.
                """, email=censored_email)

            if not userid:
                return custom_render_template("login.html", errmsg="Internal server error: Failed to fetch user")    

            sid = create_session(userid=userid, request_obj=request)
            # create the session, but dont give them the cookie yet

            if not sid:
                return custom_render_template("login.html", errmsg="Internal server error: Unable to acquire session ID")

            auth_response = get_auth_user_response(sessionID=sid)

            return auth_response
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
