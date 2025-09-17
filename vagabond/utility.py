import psycopg2 as post
import logging as log
import traceback
import re

log = log.getLogger(__name__)

DB_SUCCESS = 0
DB_FAILURE = 1
EXECUTED_NO_FETCH = 0

def rows_to_dict(rows, columns):
    return [dict(zip(columns, row)) for row in rows]

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
        return post.connect(**self.db_config)

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