
from vagabond.services import dbmanager as db
from flask import request
import logging

from vagabond.sessions.module import get_fingerprint
from vagabond.utility import deep_get

log = logging.getLogger(__name__)

def update_fingerprint_impressions(page_name: str) -> None:

    user_fingerprint = get_fingerprint() # add this to the inject context processor
    db.write(query_str="""
        INSERT INTO impressions (impression_hash, impression_hits, impression_first_visited)
        VALUES (%s, 1, NOW())
        ON CONFLICT (impression_hash)
        DO UPDATE SET impression_hits = impressions.impression_hits + 1
    """, params=(user_fingerprint,))

    raw_template_name = page_name.split(".")[0]
    log.debug(raw_template_name)

    db.write(query_str="""
        INSERT INTO impression_durations (impression_hash, impression_start, impression_page)
        VALUES (%s, NOW(), %s)
    """, params=(user_fingerprint, raw_template_name))
