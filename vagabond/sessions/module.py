from vagabond.constants import RouteError
from vagabond.flask_wrapper import error_response
from vagabond.utility import rows_to_dict, deep_get
from vagabond.dbmanager import DBManager, DBStatus
from vagabond.queries import *
from flask import Response, jsonify, make_response, request, abort, redirect, url_for
from vagabond.services import dbmanager as db
from ua_parser import parse_os, parse_user_agent, parse_device
from itsdangerous import URLSafeTimedSerializer
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timezone, timedelta

import hashlib
import logging
import secrets
import string
import os

load_dotenv(find_dotenv("secrets.env"))

log = logging.getLogger(__name__)

# generate a new token and detect collisions
# query the session token to see if it is valid
# invalidate and delete the session token

from functools import wraps


def CSRF(app):
    @app.before_request
    def csrf_protect():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            endpoint = request.endpoint
            if not endpoint:
                log.error("Missing endpoint: %s", request.full_path)
                abort(403)

            view_func = app.view_functions[request.endpoint]
            if view_func and not getattr(view_func, '_csrf_exempt', False):
                is_valid_csrf_or_abort()
            else:
                log.debug("skipping CSRF check because view was explicitly ommited")

# every function in python is an object, and instead of keeping a global list
# we can at decorator time just attach a special attribute to check with getattr
def csrf_exempt(f):

    @wraps(f)
    def decorated_func(*args, **kwargs):
        return f(*args, **kwargs)
    
    decorated_func._csrf_exempt = True

    return decorated_func

# csrf protections (stateless, itsdangerous urlsafetimed is signed and only valid within a time stamp so no need to use a DB)
# we are also using the session id and the constant salt we randomly generated, so it will always be the same
def get_csrf_token(): # we want to keep this argumentless for ease of use
    sid = get_session_id()

    if sid and is_valid_session(sessionID=sid):
        serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
        return serializer.dumps(sid, salt=os.getenv("SECURITY_PASSWORD_SALT"))

def is_valid_csrf_token(token, expiration=7200) -> str | bool:
    current_sid = get_session_id()
    serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
    try:
        sid = serializer.loads(
            token, salt=os.getenv("SECURITY_PASSWORD_SALT"), max_age=expiration
        )
        return sid == current_sid
    except Exception:
        return False
    
def is_valid_csrf_or_abort():
    token = (
        request.headers.get("X-CSRFToken")
        or request.form.get("csrf_token")
    )

    if not token or not is_valid_csrf_token(token):
        sid = get_session_id()

        log.warning("CSRF token missing or invalid for request to %s from %s", request.path, request.remote_addr)
        abort(403)


def abort_if_not_signed_in():
    if not is_user_logged_in():
        abort(401)

def redirect_if_already_logged_in(page="index"):
    if is_user_logged_in():
        return redirect( url_for(page) )

# mainly for security and analytics
def associate_fingerprint_to_session(fingerprint: str, sessionID: str) -> None:
    log.warning("associating fingerprint to session id")
    db.write(query_str="""
        UPDATE sessions_table
        SET fingerprint_id = %s
        WHERE sid = %s
    """, params=(fingerprint, sessionID,))

def get_fingerprint() -> str:
    user_agent = request.headers.get("User-Agent") or ""
    accepted_languages = request.headers.get("Accept-Language") or ""
    ip_address = request.remote_addr # is per basis of connection so never missing

    combined_fingerprint = ip_address + user_agent + accepted_languages

    hashobj = hashlib.sha256()
    hashobj.update(combined_fingerprint.encode('utf-8'))

    return hashobj.hexdigest()

# it shouldnt be ambiguous that the session is valid or not.
def get_session_id() -> str | None:
    sid = request.cookies.get("sessionID")
    return sid if is_valid_session(sessionID=sid) else None

def get_tsid(sessionID: str) -> str | None:
    if not is_valid_session(sessionID=sessionID):
        return None

    get_tsid = db.read(query_str="""
        SELECT temp_data_sid
        FROM sessions_table
        WHERE sid = %s
    """, params=(sessionID,))

    if get_tsid == DBStatus.FAILURE:
        log.critical("Failure to fetch tsid")
        return error_response(RouteError.INTERNAL_SERVER_ERROR, 500)

    tsid = deep_get(get_tsid, 0, 0)
    return tsid if tsid else None

def is_user_logged_in() -> bool:
    sid = get_session_id()
    return True if sid and is_valid_session(sessionID=sid) else False


def generate_sid() -> str:
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

# returns the sessionID or None on error, intended to be called at login and signup
def create_session(userid: str, request_obj) -> str | None:
    
    # create the supplementory temporary data sid
    temp_session_data_id = db.write(query_str=CREATE_TEMP_SESSION_DATA, fetch=True)[0][0]

    sid = generate_sid()

    while True:
        try:
            response = db.read(query_str="""
            SELECT EXISTS (
                SELECT 1 FROM sessions_table WHERE sid = %s
            );
            """, fetch=True, params=(sid,)) # since we are only checking if it exists no need to get all columns using SELECT *
        except Exception as e:
            log.critical("Failed checking unique sid: %s", e)
            return None
        sid_is_taken = deep_get(response, 0, 0)
        if not sid_is_taken:
            break
        sid = generate_sid()

    ipaddr = request_obj.remote_addr
    raw_user_agent = request_obj.headers.get("User-Agent")

    ua_os = parse_os(raw_user_agent)
    #ua_device = parse_device(raw_user_agent)
    ua_browser = parse_user_agent(raw_user_agent)

    combined_ua = f"{ua_os.family} {ua_os.major}, {ua_browser.family}"
    # [insert geolocation service tracking here]

    session_duration = timedelta(hours=2) # 7200 seconds
    expires_at = datetime.now(timezone.utc) + session_duration

    # lets create a new session in the sessions_table
    success = db.write(query_str="""
        INSERT INTO sessions_table (sid, ipaddr, user_id, display_user_agent, raw_user_agent, temp_data_sid, active, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, params=(sid, ipaddr, userid, combined_ua, raw_user_agent, temp_session_data_id, True, expires_at))

    if success == DBStatus.FAILURE:
        log.critical("Failure to create a new session for userID: %s", userid)
        return None
    
    log.debug("A new session was created successfully")

    
    return sid
    


def is_valid_session(sessionID: str) -> bool:
    # check if the session is valid (just checking the active variable and this userid)
    # get the device fingerprint
    fingerprint = get_fingerprint()

    is_session_valid = db.read(query_str="""
        SELECT 1
        FROM sessions_table
        WHERE sid = %s AND active = TRUE""", fetch=True, params=(sessionID,))
    # AND (expires_at IS NULL OR expires_at > NOW()) currently unimplemented, causing bugs
    # #  removing this for now until we can get a better solution

    return is_session_valid or False # it wasnt found or something wrong is going on

def get_userid_from_session(sessionID: str) -> str | None:
    get_userid = db.read(query_str="""
            SELECT user_id
            FROM sessions_table
            WHERE sid = %s
        """, fetch=True, params=(sessionID,))
    if not get_userid:
        return None
    return deep_get(get_userid, 0, 0)

# invalidation of a session is important
def invalidate_session(sessionID: str) -> None:
    invalidate_session = None
    n_retries = 0

    log.warning("Invalidating session of sid: %s", sessionID)

    # retry until success
    while invalidate_session != DBStatus.SUCCESS and n_retries < 3:
        invalidate_session = db.write(query_str="""
            UPDATE sessions_table
            SET active = FALSE
            WHERE sid = %s
        """, params=(sessionID,))
        n_retries += 1

    # the best we can do is put it in an easily parsable format for a db admin to fix when the db is back up
    if invalidate_session != DBStatus.SUCCESS:
        log.critical("Failed to invalidate session [%s]", sessionID)

    return None