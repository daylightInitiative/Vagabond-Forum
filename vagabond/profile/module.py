from vagabond.services import dbmanager as db
from vagabond.utility import rows_to_dict
import logging

log = logging.getLogger(__name__)

def create_profile(userID: str) -> None:

    # for now theres nothing tied to a profile but later there will be awards, titles and profile display settings
    db.write(query_str="""
        INSERT INTO profiles (profile_id)
            VALUES (%s)
    """, params=(userID,))

def get_profile_info(userID: str) -> None:
    rows, cols = db.read(query_str="""
        SELECT email, username, join_date, avatar_hash, is_2fa_enabled
        FROM users
        WHERE id = %s
    """, get_columns=True, params=(userID,))

    profile_data = rows_to_dict(rows=rows, columns=cols)
    log.debug(profile_data)
    return profile_data