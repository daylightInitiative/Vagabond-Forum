from vagabond.signup import signup_bp
from flask import request, jsonify, redirect, abort, make_response, url_for
from vagabond.sessions.module import (
    redirect_if_already_logged_in,
    create_session
)
from vagabond.signup.module import signup
from vagabond.avatar import update_user_avatar, create_user_avatar
from vagabond.flask_wrapper import custom_render_template
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

        sid = create_session(userid=userid, request_obj=request)

        if not sid:
            return custom_render_template("signup.html", errmsg="Internal server error: Unable to acquire session ID")

        # lets create the users randomly generated avatar (we dont have a cdn yet so... just in static)
        # this returns the md5 hash of the image
        avatar_url = create_user_avatar(userid)

        # update the avatar
        update_user_avatar(userID=userid, avatar_hash=avatar_url)

        log.debug("Sending session to client from signup")
        response = make_response(redirect(url_for("index")))
        response.set_cookie(key="sessionID", value=sid)
        
        return response