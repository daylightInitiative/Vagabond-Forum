import logging as log
from pathlib import Path
from datetime import datetime
import re

from flask import Response, jsonify
from vagabond.constants import MAX_URL_TITLE, RouteStatus
from vagabond.services import dbmanager as db
import secrets
import string

log = log.getLogger(__name__)

APP_FOLDER = Path(__file__).parent
ROOT_FOLDER = APP_FOLDER.parent
SQL_FOLDER = ROOT_FOLDER / "sql"

included_reload_files = []

# restart stat on all json file changes
for file in ROOT_FOLDER.iterdir():
    if 'json' in file.suffix:
        included_reload_files.append(file.absolute())

# append the rest (our sql files)
for file in SQL_FOLDER.iterdir():
    if 'sql' in file.suffix:
        included_reload_files.append(file.absolute())

password_alphabet = string.ascii_letters + string.digits + '#*?'

def generate_random_password(length: int) -> str:
    return ''.join(secrets.choice(password_alphabet) for i in range(length))

"""
Provides a display version of someones email used for codes and profile info
    get_censored_email("john@example.com") -> joh**********
"""
def get_censored_email(email: str):
    return email[0:3] + ('*' * (len(email) - 3))

# used to help better organize many emails of internal errors
def get_email_subject_date():
    now = datetime.now()
    weekday = now.strftime('%a')
    month = now.strftime('%b')
    return f"{weekday}, {month} {now.day}"

# ISO 8601 format with timezone offset (postgres like so its standardized)
def get_current_TIMESTAMPZ():
    return datetime.now().astimezone().isoformat()

# having to manually stop and start the flask application again everytime you change a sql or .json file can be quite troublesome
def read_sql_file(filename):
    try:
        found_sql_file = SQL_FOLDER / filename
        if found_sql_file.exists():
            with open(found_sql_file, mode='r') as f:
                filetext = f.read()
                return filetext
    except FileNotFoundError:
        raise Exception(f"{filename} sql query was not found")

def rows_to_dict(rows, columns):
    return [dict(zip(columns, row)) for row in rows]

def title_to_content_hint(title: str) -> str:
    # we only want to get normal characters and normal numbers, and then seperate them with a "-"
    # adding _ explicitly because its designated as a word character in the \W internally
    text = title.lower()[:MAX_URL_TITLE]
    return re.sub(r'[\W_]+', '-', text).strip('-')

# once we setup a server, py3-validate-email using this for enhanced protection
def is_valid_email_address(email: str) -> bool:
    pattern = r"\"?([-a-zA-Z0-9.`?{}]+@\w+\.\w+)\"?"
    return re.match(pattern, email)

def deep_get(data, *indices):
    try:
        for i in indices:
            data = data[i]
        return data
    except (IndexError, KeyError, TypeError) as e:
        # frame = inspect.stack()[1]

        # # since we use deep_get here in try except for safety, it swallows the error (until i figure out the api we're just gonna disable)
        # caller_info = f"{frame.filename}:{frame.lineno} in {frame.function}()"
        # log.warning("Failed to access element at [%s]: %d levels deep.\nerror: %s\nmethod call from: %s", data, i, e, caller_info)
        return None

# when you need state, error handling but also functions I find that using a class here works nice

def is_valid_userid(userID: str) -> bool:
    if not userID.isdigit():
        log.warning("%s failed a digit userid check.", userID)
        return False
    
    userid_exists = db.read(query_str="""
        SELECT EXISTS (
            SELECT 1
            FROM users
            WHERE id = %s AND account_locked = FALSE
        );
    """, params=(userID,))
    return deep_get(userid_exists, 0, 0) or False

def get_email_from_userid(userid: str) -> str | bool:
    get_email = db.read(query_str="""
            SELECT email
            FROM users
            WHERE id = %s
        """, fetch=True, params=(userid,))
    return deep_get(get_email, 0, 0) or False

def contains_json_key_or_error(dictionary: dict, keydict: dict) -> None:
    from flask_wrapper import error_response
    for key, value in keydict.items():
        key_exists = dictionary.get(key)
        if not key_exists or not type(key_exists) == value:
            return error_response(RouteStatus.INVALID_FORM_DATA, 422)
    return None

def get_username_from_userid(userid: str) -> str | None:
    get_username = db.read(query_str="""
            SELECT username
            FROM users
            WHERE id = %s
        """, fetch=True, params=(userid,))
    return deep_get(get_username, 0, 0) or None

def get_group_owner(groupID: str) -> str | None:
    get_group_owner = db.read(query_str="""
        SELECT group_owner
        FROM message_recipient_group
        WHERE groupid = %s
    """, params=(groupID,))
    return deep_get(get_group_owner, 0, 0) or None

def get_group_members(groupID: str) -> tuple[int] | None:
    get_member_ids = db.read(query_str="""
        SELECT *
        FROM message_group_users
        WHERE group_id = %s      
    """, params=(groupID,))
    return deep_get(get_member_ids, 0) or None

def get_groupid_from_message(messageID: str) -> str | None:
    get_groupid = db.read(query_str="""
            SELECT msg_group_id
            FROM user_messages
            WHERE id = %s
        """, fetch=True, params=(messageID,))
    return deep_get(get_groupid, 0, 0) or None

def get_userid_from_email(email: str) -> str | bool:
    get_userid = db.read(query_str="""
            SELECT id
            FROM users
            WHERE email = %s
        """, fetch=True, params=(email,))
    return deep_get(get_userid, 0, 0) or False