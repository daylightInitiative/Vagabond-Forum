
from queries import *
from utility import DBManager, get_userid_from_email
import logging
import argon2

log = logging.getLogger(__name__)
ph = argon2.PasswordHasher(hash_len=24) # 16 is enough entrophy but we want to be more secure

# returns true and signs the user up on success, on failure false is returned with a error message.
def signup(db: DBManager, email: str, username: str, password: str) -> tuple[bool, str]:
    try:
        
        username = username.strip()
        if not username or len(username) > 20 or len(username) < 3:
            return False, "Invalid username, must be greater than 3 characters long and less than 20"

        email = email.strip()
        if not email or not '@' in email: #probably will use email regex for future verification
            return False, "Email is invalid"
        # if a user already exists with this email then we bail
        user_already_exists = get_userid_from_email(db=db, email=email)

        if user_already_exists:
            return False, "A User has already registered with the given email"
        
        # now lets hash the password, create the user and log them in (log in happens in main)
        hashed_password = ph.hash(password=password)

        new_user_id = db.write(query_str=INIT_SITE_ACCOUNTS, fetch=True, params=(
            email, username, False, False, hashed_password, "127.0.0.1", False,))[0][0]
        
    except Exception as e:
        log.error("Unexpected error during login", exc_info=e)
        return False, "Internal Server Error"
    
    log.debug("Successful login")
    return new_user_id, "Login Successful"