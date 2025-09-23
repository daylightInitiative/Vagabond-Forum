
from vagabond.queries import *
from vagabond.utility import get_userid_from_email, is_valid_email_address, deep_get
from vagabond.dbmanager import DBManager, DBStatus
import logging
import bcrypt

log = logging.getLogger(__name__)

# returns true upon a successful authentication, false upon incorrect credentials
def is_valid_login(db: DBManager, email: str, password: str) -> tuple[bool, str]:
    try:
        email = email.strip()
        if not email or not is_valid_email_address(email=email): #probably will use email regex for future verification
            return False, "Email is invalid"
        # fetch the hashed_password row from the user associated with this username
        
        userid = get_userid_from_email(db=db, email=email)
        
        if not userid:
            return False, "Incorrect email or password"
        
        is_banned = db.read(query_str="""
            SELECT id, account_locked
            FROM users
            WHERE id = %s and account_locked = TRUE
        """, fetch=True, params=(userid,))

        if is_banned and deep_get(is_banned, 0, 0) == True:
            return False, "Account associated with email has been disabled."

        get_hash = db.read(query_str="""
            SELECT hashed_password
            FROM users
            WHERE id = %s
        """, fetch=True, params=(userid,))

        if not get_hash:
            log.warning("Cannot retrieve hash")
            return False, "Unable to fetch"
        
        hash = deep_get(get_hash, 0, 0)

        provided_password = password.encode('utf-8')
        hashed_password = hash.encode('utf-8')
        result = bcrypt.checkpw(provided_password, hashed_password)

        if result == False:
            return False, "Incorrect email or password"
    except Exception as e:
        log.error("Unexpected error during login", exc_info=e)
        return False, "Internal Server Error"
    
    log.debug("Successful login")
    return True, "Login Successful"




