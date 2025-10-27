
import psycopg2 as post
import logging as log
from enum import Enum
import traceback


log = log.getLogger(__name__)


class DBStatus(Enum):
    SUCCESS = 0
    FAILURE = 1
    EXECUTED_NO_FETCH = 0

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
                return DBStatus.SUCCESS
            except Exception as e:
                log.critical("Database write query failed: %s", e)
                conn.rollback()
                traceback.print_exc()
                raise
        return DBStatus.FAILURE


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
                    return DBStatus.EXECUTED_NO_FETCH
        except Exception as e:
            log.critical("Database query failed: %s", e)
            traceback.print_exc()
            raise
        return DBStatus.FAILURE