from vagabond.sessions.module import (
    redirect_if_already_logged_in,
    create_session, invalidate_session,
    get_session_id
)
from vagabond.utility import get_userid_from_email
from vagabond.login import login_bp
from vagabond.login.module import is_valid_login
from vagabond.services import limiter
from flask import request, render_template, make_response, redirect, url_for, jsonify
import logging

log = logging.getLogger(__name__)

@login_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("125 per minute", methods=["GET"])
@limiter.limit("70 per minute", methods=["POST"])
def serve_login():

    redirect_if_already_logged_in()

    if request.method == "GET":
        return render_template("login.html")
    elif request.method == "POST":

        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            return jsonify({"error": "Invalid form data"}), 422
        
        is_authenticated, errmsg = is_valid_login(email=email, password=password)
        
        if is_authenticated:
        
            # lets get the userid
            userid = get_userid_from_email(email=email)
            sid = create_session(userid=userid, request_obj=request)

            if not userid:
                return render_template("login.html", errmsg="Internal server error: Failed to fetch user")    

            if not sid:
                return render_template("login.html", errmsg="Internal server error: Unable to acquire session ID")

            log.debug("Sending session to client")
            response = make_response(redirect(url_for("index")))
            response.set_cookie(key="sessionID", value=sid)

            return response
        else:
            return render_template("login.html", errormsg=errmsg)

@login_bp.route('/logout')
def logout():
    sid = get_session_id()
    if sid:
        invalidate_session(sessionID=sid)

    return redirect(url_for('login.serve_login'))
