from pathlib import Path

APP_FOLDER = Path(__name__).parent
ROOT_FOLDER = APP_FOLDER.parent
SQL_FOLDER = ROOT_FOLDER / "sql"

def read_sql_file(filename):
    try:
        found_sql_file = SQL_FOLDER / filename
        if found_sql_file.exists():
            with open(found_sql_file, mode='r') as f:
                filetext = f.read()
                return filetext
    except FileNotFoundError:
        raise Exception(f"{filename} sql query was not found")


# init db
INIT_DB_TABLES = read_sql_file("init_db_tables.sql")

# page queries
QUERY_NEWS_POSTS = read_sql_file("query_news_posts.sql")
QUERY_PAGE_POSTS = read_sql_file("query_page_posts.sql")
QUERY_PAGE_REPLIES = read_sql_file("query_page_replies.sql")
VIEW_POST_BY_ID = read_sql_file("view_post_by_id.sql")

# user queries
QUERY_USERID_BY_EMAIL = read_sql_file("query_userid_by_email.sql")

# predefined accounts (startup employees or admins)
INIT_SITE_ACCOUNTS = read_sql_file("init_site_account.sql")
SHOW_SERVER_VERSION = 'SHOW server_version;'
