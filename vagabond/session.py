from vagabond.utility import rows_to_dict, deep_get
from vagabond.dbmanager import DBManager, DBStatus
from vagabond.queries import *
from flask import request
from ua_parser import parse_os, parse_user_agent, parse_device
import logging
import secrets
import string

log = logging.getLogger(__name__)
# generate a new token and detect collisions
# query the session token to see if it is valid
# invalidate and delete the session token

def generate_sid() -> str:
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

# returns the sessionID or None on error, intended to be called at login and signup
def create_session(db: DBManager, userid: str, request_obj) -> str | None:
    
    # create the supplementory temporary data sid
    temp_session_data_id = db.write(query_str=CREATE_TEMP_SESSION_DATA, fetch=True)[0][0]

    sid = generate_sid()

    while True:
        try:
            response = db.read(query_str="""
            SELECT EXISTS (
                SELECT * FROM sessions_table WHERE sid = %s
            );
            """, fetch=True, params=(sid,))
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

    # lets create a new session in the sessions_table
    success = db.write(query_str="""
        INSERT INTO sessions_table (sid, ipaddr, user_id, display_user_agent, raw_user_agent, temp_data_sid, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, params=(sid, ipaddr, userid, combined_ua, raw_user_agent, temp_session_data_id, True))

    if success == DBStatus.FAILURE:
        log.critical("Failure to create a new session for userID: %s", userid)
        return None
    
    log.debug("A new session was created successfully")

    
    return sid

def is_valid_session(db: DBManager, sessionID: str) -> bool:
    # check if the session is valid (just checking the active variable and this userid)
    is_session_valid = db.read(query_str="""
        SELECT *
        FROM sessions_table
        WHERE sid = %s and active = TRUE
    """, fetch=True, params=(sessionID,))

    return is_session_valid or False # it wasnt found or something wrong is going on

def get_userid_from_session(db: DBManager, sessionID: str) -> str:
    get_userid = db.read(query_str="""
            SELECT user_id
            FROM sessions_table
            WHERE sid = %s
        """, fetch=True, params=(sessionID,))
    if not get_userid:
        return None
    return deep_get(get_userid, 0, 0)

# invalidation of a session is important
def invalidate_session(db: DBManager, sessionID: str) -> None:
    invalidate_session = None
    n_retries = 0

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