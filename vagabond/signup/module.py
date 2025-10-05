
from vagabond.queries import *
from vagabond.utility import is_valid_email_address, deep_get, get_userid_from_email
from vagabond.dbmanager import DBManager, DBStatus
from vagabond.services import dbmanager
import logging
import bcrypt

log = logging.getLogger(__name__)

# returns true and signs the user up on success, on failure false is returned with a error message.
def signup(email: str, username: str, password: str) -> tuple[bool|int, str]:
    try:
        
        username = username.strip()
        if not username or len(username) > 20 or len(username) < 3:
            return False, "Invalid username, must be greater than 3 characters long and less than 20"

        email = email.strip()
        if not email or not is_valid_email_address(email=email): #probably will use email regex for future verification
            return False, "Email is invalid"
        # if a user already exists with this email then we bail
        user_already_exists = get_userid_from_email(email=email)

        if user_already_exists:
            return False, "A User has already registered with the given email"
        
        # now lets hash the password, create the user and log them in (log in happens in main)
        password_salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), password_salt)

        safe_salt = password_salt.decode('utf-8')
        safe_password = hashed_password.decode('utf-8')
        
        # create the salt, save it
        new_user_id = dbmanager.write(query_str=INIT_SITE_ACCOUNTS, fetch=True, params=(
            email, username, False, False, safe_password, safe_salt, False,))
        
        if new_user_id == DBStatus.FAILURE:
            return False, "Unable to fetch"
        
        user_id = deep_get(new_user_id, 0, 0)
        
    except Exception as e:
        log.error("Unexpected error during login", exc_info=e)
        return False, "Internal Server Error"
    
    log.debug("Successful Signup")
    return user_id, "Signup Successful"