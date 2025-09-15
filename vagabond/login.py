
from queries import *
from utility import DBManager, get_userid_from_email
import logging
import argon2

log = logging.getLogger(__name__)
ph = argon2.PasswordHasher(hash_len=24) # 16 is enough entrophy but we want to be more secure
#https://argon2-cffi.readthedocs.io/en/stable/howto.html

# returns true upon a successful authentication, false upon incorrect credentials
def is_valid_login(db: DBManager, email: str, password: str) -> tuple[bool, str]:
    try:
        email = email.strip()
        if not email or not '@' in email: #probably will use email regex for future verification
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

        if is_banned and is_banned[0][0] == True:
            return False, "Account associated with email has been disabled."

        get_hash = db.read(query_str="""
            SELECT hashed_password
            FROM users
            WHERE id = %s
        """, fetch=True, params=(userid,))

        if not get_hash:
            log.warning("Cannot retrieve hash")
            return False, "Incorrect email or password"
        
        hash = get_hash[0][0]

        ph.verify(hash, password)
        if ph.check_needs_rehash(hash):
            new_hash = ph.hash(password)
            log.debug(f"password for userid {userid} needs rehashing, attempting to rehash")
            db.write(query_str="""
                UPDATE users
                SET hashed_password = %s
                WHERE id = %s
            """, params=(new_hash, userid,))
    except argon2.exceptions.VerifyMismatchError: # blatently wrong password
        return False, "Incorrect email or password"
    except Exception as e:
        log.error("Unexpected error during login", exc_info=e)
        return False, "Internal Server Error"
    
    log.debug("Successful login")
    return True, "Login Successful"




