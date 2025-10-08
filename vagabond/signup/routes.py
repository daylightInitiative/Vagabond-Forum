from vagabond.signup import signup_bp
from flask import request, jsonify, redirect, abort, make_response, url_for
from vagabond.sessions.module import (
    redirect_if_already_logged_in,
    associate_fingerprint_to_session,
    get_fingerprint,
    create_session
)
from vagabond.services import limiter
from vagabond.profile.module import create_profile
from vagabond.signup.module import signup
from vagabond.signup.email import generate_token, confirm_token, send_confirmation_code
from vagabond.avatar import update_user_avatar, create_user_avatar
from vagabond.flask_wrapper import custom_render_template
from vagabond.utility import get_userid_from_email

import logging

log = logging.getLogger(__name__)

@signup_bp.route('/signup', methods=['GET', 'POST'])
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
            return jsonify({"error": "Invalid form data"}), 400
        
        userid, errmsg = signup(email=email, username=username, password=password)

        if not userid:
            return custom_render_template("signup.html", errmsg=errmsg)
        
        email_token = generate_token(email=email)
        send_confirmation_code(email=email, code=email_token)
        
        return custom_render_template("confirm_email.html", email=email)

        
    

@signup_bp.route("/confirm", methods=["GET"])
def confirm_signup_code():
    
    signup_code = request.args.get("token")

    if not signup_code:
        return jsonify({"error": "Bad token"}), 422
    
    decoded_email = confirm_token(token=signup_code)

    if not decoded_email:
        return jsonify({"error": "Expired token"}), 422

    userid = get_userid_from_email(email=decoded_email)

    if not userid:
        return jsonify({"error": "User not found"}), 404

    sid = create_session(userid=userid, request_obj=request)

    if not sid:
        return custom_render_template("signup.html", errmsg="Internal server error: Unable to acquire session ID")

    # lets create the users randomly generated avatar (we dont have a cdn yet so... just in static)
    # this returns the md5 hash of the image
    avatar_url = create_user_avatar(userid)

    # update the avatar
    update_user_avatar(userID=userid, avatar_hash=avatar_url)

    # create a profile for the user
    create_profile(userID=userid)

    log.debug("Sending session to client from signup")
    response = make_response(redirect(url_for("index")))
    response.set_cookie(key="sessionID", value=sid, max_age=7200)

    user_fingerprint = get_fingerprint()
    associate_fingerprint_to_session(fingerprint=user_fingerprint, sessionID=sid)
    
    return response