import psycopg2 as post
import logging as log
from pathlib import Path
import traceback
import re
from vagabond.constants import MAX_URL_TITLE

log = log.getLogger(__name__)

DB_SUCCESS = 0
DB_FAILURE = 1
EXECUTED_NO_FETCH = 0

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
class DBManager:
    def __init__(self, config):
        self.db_config = config.db_config

    # i'm pretty sure _ hints you arent supposed to call it
    def _get_connection(self):
        try:
            return post.connect(**self.db_config)
        except Exception as e:
            log.critical("Failure upon establishing a connection to the database: %s", e)
            raise RuntimeError("Database connection failed") # its better to error here

    # avoids redundant calls to .commit() and fetch
    # TODO: add bit flagging for fetch and commit to unionize this function
    # https://www.psycopg.org/docs/cursor.html cursor.description gives column objects containing the column names
    def write(self, query_str, fetch=False, params=None):
        """Executes a query on the db, then calls .commit()"""
        with self._get_connection() as conn:
            try:
                with conn.cursor() as cur:

                    if params:
                        cur.execute(query_str, params)
                    else:
                        cur.execute(query_str)
                    conn.commit()
                    if fetch:
                        results = cur.fetchall()
                        return results
                return DB_SUCCESS
            except Exception as e:
                log.critical("Database write query failed: %s", e)
                conn.rollback()
                traceback.print_exc()
                raise
        return DB_FAILURE


    def read(self, query_str, fetch=True, get_columns=False, params=None):
        """Executes a query on the db, read only"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    
                    if params:
                        cur.execute(query_str, params)
                    else:
                        cur.execute(query_str)

                    if fetch:
                        results = cur.fetchall()
                        if get_columns and cur.description:

                            column_names = [col.name for col in cur.description]
                            return results, column_names
                        return results
                    return EXECUTED_NO_FETCH
        except Exception as e:
            log.exception("Database query failed: %s", e)
            traceback.print_exc()
            raise
        return DB_FAILURE
    
def get_userid_from_email(db: DBManager, email: str) -> str:
    get_userid = db.read(query_str="""
            SELECT id
            FROM users
            WHERE email = %s
        """, fetch=True, params=(email,))
    if not get_userid:
        return None
    return deep_get(get_userid, 0, 0)