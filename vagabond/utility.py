import logging as log
from pathlib import Path
import re
from vagabond.constants import MAX_URL_TITLE
from vagabond.dbmanager import DBManager, DBStatus
from vagabond.services import dbmanager

log = log.getLogger(__name__)

APP_FOLDER = Path(__file__).parent
ROOT_FOLDER = APP_FOLDER.parent
SQL_FOLDER = ROOT_FOLDER / "sql"

included_reload_files = []
main_config_file = ROOT_FOLDER / "config.json"

included_reload_files.append(main_config_file)

# append the rest (our sql files)
for file in SQL_FOLDER.iterdir():
    if 'sql' in file.suffix:
        included_reload_files.append(file.absolute())


"""
Provides a display version of someones email used for codes and profile info
    get_censored_email("john@example.com") -> joh**********
"""
def get_censored_email(email: str):
    return email[0:3] + ('*' * (len(email) - 3))

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
        log.debug("Failed to access element at [%s]: %d levels deep: %s", data, i, e)
        return None

# when you need state, error handling but also functions I find that using a class here works nice
    
def get_userid_from_email(email: str) -> str:
    get_userid = dbmanager.read(query_str="""
            SELECT id
            FROM users
            WHERE email = %s
        """, fetch=True, params=(email,))
    if not get_userid:
        return None
    return deep_get(get_userid, 0, 0)