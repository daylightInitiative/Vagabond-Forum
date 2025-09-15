
from queries import *
from utility import DBManager
import logging
import argon2

log = logging.getLogger(__name__)
ph = argon2.PasswordHasher(hash_len=24) # 16 is enough entrophy but we want to be more secure
#https://argon2-cffi.readthedocs.io/en/stable/howto.html

# returns true upon a successful authentication, false upon incorrect credentials
def is_valid_login(db: DBManager, email: str, password: str) -> bool:
    try:
        email = email.strip()
        if not email:
            raise ValueError("Email is missing")
        # fetch the hashed_password row from the user associated with this username
        userid = db.read(query_str="""
            SELECT id
            FROM users
            WHERE email = %s
        """, fetch=True, params=(email,))[0][0]
        
        if userid is None:
            log.warning(userid, "Cannot retrieve userid")
            return False

        hash = db.read(query_str="""
            SELECT hashed_password
            FROM users
            WHERE id = %s
        """, fetch=True, params=(userid,))[0][0]

        if hash is None:
            log.warning(hash, "Cannot retrieve hash")
            return False

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
        return False
    except Exception as e:
        log.error("Unexpected error during login", exc_info=e)
        return False
    
    log.debug("Successful login")
    return True




