from utility import DBManager, rows_to_dict, deep_get
from utility import DB_SUCCESS, DB_FAILURE
from queries import *
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
def create_session(db: DBManager, userid: str, ipaddr: str) -> str | None:
    
    # create the supplementory temporary data sid
    temp_session_data_id = db.write(query_str=CREATE_TEMP_SESSION_DATA, fetch=True)[0][0]
    print("tsid: ", temp_session_data_id)

    sid = generate_sid()
    print(sid, len(sid))

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
        print("sid taken: ",sid_is_taken)
        if not sid_is_taken:
            break
        sid = generate_sid()

    # lets create a new session in the sessions_table
    success = db.write(query_str="""
        INSERT INTO sessions_table (sid, ipaddr, user_id, temp_data_sid, active)
            VALUES (%s, %s, %s, %s, %s)
    """, params=(sid, ipaddr, userid, temp_session_data_id, True))

    log.debug("passed the existance check")

    if success != DB_SUCCESS:
        log.critical("Failure to create a new session for userID: %s", userid)
        return None
    
    return sid

def is_valid_session(db: DBManager, sessionID: str) -> bool:
    # check if the session is valid (just checking the active variable and this userid)
    is_session_valid = db.read(query_str="""
        SELECT *
        FROM sessions_table
        WHERE sid = %s and active = TRUE
    """, fetch=True, params=(sessionID,))
    print(is_session_valid)
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

def invalidate_session(db: DBManager, sessionID: str) -> None:
    invalidate_session = db.write(query_str="""
        UPDATE sessions_table
        SET active = FALSE
        WHERE sid = %s
    """, params=(sessionID,))
    return None