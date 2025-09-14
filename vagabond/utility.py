import psycopg2 as post
import logging
import traceback

log = logging.getLogger(__name__)

def rows_to_dict(rows, columns):
    return [dict(zip(columns, row)) for row in rows]

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
            except Exception as e:
                log.critical("Database write query failed")
                conn.rollback()
                traceback.print_exc()
                raise
        return None


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
                    
        except Exception as e:
            log.exception("Database query failed")
            traceback.print_exc()
            raise
        return None