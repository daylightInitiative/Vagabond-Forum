from vagabond.utility import read_sql_file

# init db
INIT_DB_TABLES = read_sql_file("init_db_tables.sql")

# v2 forum queries
QUERY_FORUM_CATEGORIES = read_sql_file("query_forum_categories.sql")

# page queries
QUERY_NEWS_POSTS = read_sql_file("query_news_posts.sql")
QUERY_PAGE_POSTS = read_sql_file("query_page_posts.sql")
QUERY_PAGE_REPLIES = read_sql_file("query_page_replies.sql")
VIEW_POST_BY_ID = read_sql_file("view_post_by_id.sql")

# session queries
CREATE_TEMP_SESSION_DATA = read_sql_file("create_temp_session_data.sql")

# user queries
QUERY_USERID_BY_EMAIL = read_sql_file("query_userid_by_email.sql")

# predefined accounts (startup employees or admins)
INIT_SITE_ACCOUNTS = read_sql_file("init_site_account.sql")
SHOW_SERVER_VERSION = 'SHOW server_version;'
