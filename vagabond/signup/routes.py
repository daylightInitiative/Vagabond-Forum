from vagabond.constants import RouteStatus
from vagabond.signup import signup_bp
from flask import request, jsonify, redirect, abort, make_response, url_for
from vagabond.sessions.module import (
    redirect_if_already_logged_in,
    associate_fingerprint_to_session,
    get_fingerprint,
    create_session,
    csrf_exempt
)
from vagabond.services import limiter
from vagabond.profile.module import create_profile
from vagabond.signup.module import signup
from vagabond.email import generate_token, confirm_token, send_signup_code
from vagabond.avatar import update_user_avatar, create_user_avatar
from vagabond.flask_wrapper import custom_render_template
from vagabond.utility import get_userid_from_email

import logging

log = logging.getLogger(__name__)


@signup_bp.route('/signup', methods=['GET', 'POST'])
@csrf_exempt
def signup_page():
    
    redirect_if_already_logged_in()

    if request.method == "GET":

        # if the user is already signed in, redirect them away
        return custom_render_template("signup.html")
    elif request.method == "POST":
        
        email = request.form.get('email', type=str)
        username = request.form.get('username', type=str)
        password = request.form.get('password', type=str)
        
        if not email or not username or not password:
            return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 422
        
        userid, errmsg = signup(email=email, username=username, password=password)

        if not userid:
            return custom_render_template("signup.html", errmsg=errmsg)
        
        email_token = generate_token(email=email)
        send_signup_code(email=email, code=email_token)
        
        return custom_render_template("confirm_email.html", text="""
            A temporary sign up link has been sent to the email above, it will expire in one hour.
        """, email=email)

        


@signup_bp.route("/confirm", methods=["GET"])
@csrf_exempt
def confirm_email_code():
    
    email_code = request.args.get("token")
    code_type = request.args.get("token_type")

    if not code_type:
        return jsonify({"error": RouteStatus.INVALID_FORM_DATA.value}), 422

    if not email_code:
        return jsonify({"error": RouteStatus.BAD_TOKEN.value}), 422
    
    decoded_email = confirm_token(token=email_code)

    if not decoded_email:
        return jsonify({"error": RouteStatus.EXPIRED_TOKEN.value}), 422

    userid = get_userid_from_email(email=decoded_email)

    if not userid:
        return jsonify({"error": RouteStatus.INVALID_USER_ID.value}), 404

    sid = create_session(userid=userid, request_obj=request)

    if not sid:
        return custom_render_template("signup.html", errmsg="Internal server error: Unable to acquire session ID")

    if code_type == "Signup":

        # lets create the users randomly generated avatar (we dont have a cdn yet so... just in static)
        # this returns the md5 hash of the image
        avatar_url = create_user_avatar(userid)

        # update the avatar
        update_user_avatar(userID=userid, avatar_hash=avatar_url)

        # create a profile for the user
        create_profile(userID=userid)

    auth_response = redirect(url_for('session.setup_session', sid=sid))
    return auth_response
