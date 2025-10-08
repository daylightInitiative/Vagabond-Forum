from vagabond.sessions.module import get_fingerprint
from flask import render_template
import logging

from vagabond.services import dbmanager
log = logging.getLogger(__name__)

def custom_render_template(template_name: str, **context):

    user_fingerprint = get_fingerprint() # add this to the inject context processor
    dbmanager.write(query_str="""
        INSERT INTO impressions (impression_hash, impression_hits, impression_first_visited)
        VALUES (%s, 1, NOW())
        ON CONFLICT (impression_hash)
        DO UPDATE SET impression_hits = impressions.impression_hits + 1
    """, params=(user_fingerprint,))

    raw_template_name = template_name.split(".")[0]
    log.debug(raw_template_name)

    dbmanager.write(query_str="""
        INSERT INTO impression_durations (impression_hash, impression_start, impression_page)
        VALUES (%s, NOW(), %s)
    """, params=(user_fingerprint, raw_template_name))
    return render_template(template_name, **context)