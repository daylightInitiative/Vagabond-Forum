
def read_sql_file(filename):
    try:
        with open(filename, mode='r') as f:
            filetext = f.read()
            return filetext
    except FileNotFoundError:
        raise Exception(f"{filename} sql query was not found")


QUERY_NEWS_POSTS = read_sql_file("query_news_posts.sql")
QUERY_PAGE_POSTS = read_sql_file("query_page_posts.sql")
QUERY_PAGE_REPLIES = read_sql_file("query_page_replies.sql")
VIEW_POST_BY_ID = read_sql_file("view_post_by_id.sql")
INIT_DB_TABLES = read_sql_file("init_database_tables.sql")


SHOW_SERVER_VERSION = 'SHOW server_version;'
