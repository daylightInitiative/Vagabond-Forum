
CREATE TABLE IF NOT EXISTS webstats (
    hits INT NOT NULL DEFAULT 0,
    visited_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
INSERT INTO webstats (hits) VALUES (0);

-- we're going to fingerprint by useragent and some other information like google would
CREATE TABLE IF NOT EXISTS impressions (
    impression_hash VARCHAR(64) UNIQUE PRIMARY KEY, -- ipaddress useragent acceptedlanguages (sha256)
    impression_hits BIGINT NOT NULL DEFAULT 0,
    impression_first_visited TIMESTAMPTZ DEFAULT NULL
);

-- if we want it to be 1:1 we key by the impression_hash, otherwise like users we key by the serial id
-- also if you use a serial you dont need ON CONFLICT (tsid) DO NOTHING (or do something...?)
CREATE TABLE IF NOT EXISTS impression_durations (
    id SERIAL PRIMARY KEY,
    impression_hash VARCHAR(64) NOT NULL,
    FOREIGN KEY (impression_hash) REFERENCES impressions(impression_hash),
    impression_page VARCHAR(255) NOT NULL,
    impression_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),        -- when an anonymous session starts ()
    impression_end TIMESTAMPTZ DEFAULT NULL                                 -- when an anonymous session ends ()
);

CREATE TABLE IF NOT EXISTS referrer_links (
    link_origin VARCHAR(255) PRIMARY KEY,
    hits BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS exitPages (
    pagePath VARCHAR(255) PRIMARY KEY, -- you can use other types as primary keys in tables
    hits BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(20) UNIQUE NOT NULL CHECK (char_length(username) >= 3),
    account_locked BOOLEAN NOT NULL DEFAULT FALSE,
    loginAttempts INT NOT NULL DEFAULT 0,
    is_online BOOLEAN NOT NULL DEFAULT FALSE,
    hashed_password VARCHAR(60) NOT NULL, -- bcrypt hash length
    password_salt VARCHAR(30) NOT NULL, -- bcrypt salt length default rounds
    user_role VARCHAR(10) NOT NULL,
    is_2fa_enabled BOOLEAN DEFAULT FALSE,
    avatar_hash VARCHAR(90), -- '/static/avatars/firstbyte/secondbyte/sha256hash.jpg = 90 in length
    lastSeen TIMESTAMPTZ DEFAULT NOW(),
    join_date TIMESTAMPTZ DEFAULT NOW()
);
-- using TIMESTAMPZ to account for different timezones

CREATE TABLE IF NOT EXISTS message_recipient_group (
    groupid SERIAL PRIMARY KEY,
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    last_message TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_messages (
    id SERIAL PRIMARY KEY,
    contents VARCHAR(500) NOT NULL,
    creator_id BIGINT NOT NULL REFERENCES users(id),
    -- msg_group is a way of mass messaging, but also the ability for one to one messaging
    msg_group_id BIGINT NOT NULL REFERENCES message_recipient_group(groupid),
    reply_id BIGINT REFERENCES user_messages(id),
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ -- soft deletion
);

CREATE TABLE IF NOT EXISTS edited_messages (
    id SERIAL PRIMARY KEY,
    edited_at TIMESTAMPTZ DEFAULT NOW(),
    original_contents VARCHAR(500) NOT NULL,
    message_id BIGINT NOT NULL REFERENCES user_messages(id)
);

CREATE TABLE IF NOT EXISTS message_group_users (
    group_id BIGINT NOT NULL REFERENCES message_recipient_group(groupid) ON DELETE CASCADE,
     -- users are never deleted, so we dont have to worry about this
    user_id BIGINT NOT NULL REFERENCES users(id),
    added_at TIMESTAMPTZ DEFAULT NOW(),

    -- this is called a composite primary key
    -- it keeps a user from going into the group twice
    PRIMARY KEY (group_id, user_id)
);

CREATE TABLE IF NOT EXISTS temp_session_data (
    tempid SERIAL PRIMARY KEY,
    draft_text VARCHAR(2000) DEFAULT '' NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- instead of worrying about global uniqueness and all of this confusing on conflict stuff, lets isolate the latest 2fa code
-- to the session's temp session data
CREATE TABLE IF NOT EXISTS verification_codes (
    temp_session_id BIGINT PRIMARY KEY,
    code VARCHAR(6) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 hour',
    FOREIGN KEY (temp_session_id) REFERENCES temp_session_data(tempid) ON DELETE CASCADE
);

-- this table is to keep track of admin's actions such as banning, shadowbanning and etc
-- TODO: INSTALL PG_CRON EXTENSION FOR CLEANUP OF VERIFICATION CODES

CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    profile_id INT NOT NULL,
    FOREIGN KEY (profile_id) REFERENCES users(id),
    description VARCHAR(500) NOT NULL DEFAULT ''
);



CREATE TABLE IF NOT EXISTS sessions_table (
    id SERIAL PRIMARY KEY,
    sid VARCHAR(32) UNIQUE NOT NULL,
    ipaddr inet NOT NULL,
    user_id INT NOT NULL,
    display_user_agent VARCHAR(255) NOT NULL DEFAULT 'Unknown, Unknown',
    raw_user_agent VARCHAR(2048) NOT NULL DEFAULT 'Unknown', -- increasing the raw ua size so we get all of it
    fingerprint_id VARCHAR(64), -- the sha-256 hash of the fingerprint
    temp_data_sid INT NOT NULL,
    lastLogin TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (temp_data_sid) REFERENCES temp_session_data(tempid)
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_type VARCHAR(8) NOT NULL, -- appeal, support, report, feedback
    ticket_status VARCHAR(25) NOT NULL, -- approved, needs_investigation, under_review
    title VARCHAR(64) NOT NULL,
    contents VARCHAR(2048) NOT NULL,
    reporter_userid BIGINT NOT NULL,
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    solved_at TIMESTAMPTZ,
    ticket_conclusion VARCHAR(2048) NOT NULL DEFAULT 'No conclusion provided',
    FOREIGN KEY (reporter_userid) REFERENCES users(id)
);

-- title, contents, pinned, author
CREATE TABLE IF NOT EXISTS news_feed (
    id SERIAL PRIMARY KEY,
    title VARCHAR(250) NOT NULL,
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    contents VARCHAR(2000) NOT NULL,
    author BIGINT NOT NULL REFERENCES users (id),
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ -- soft deletion
);

CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(30) NOT NULL,
    category_locked BOOLEAN NOT NULL
);

-- category_id, title, contents, author, url_title
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    category_id BIGINT NOT NULL,
    title VARCHAR(250) NOT NULL,
    views INT NOT NULL DEFAULT 0,
    contents VARCHAR(2000) NOT NULL,
    author BIGINT NOT NULL REFERENCES users (id),
    url_title VARCHAR(40) NOT NULL DEFAULT '',
    post_locked BOOLEAN NOT NULL DEFAULT FALSE,
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ DEFAULT NULL, -- soft deletion
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS replies (
    id SERIAL PRIMARY KEY,
    parent_post_id INTEGER NOT NULL,
    contents VARCHAR(500) NOT NULL,
    author BIGINT NOT NULL REFERENCES users (id),
    deleted_at TIMESTAMPTZ DEFAULT NULL, -- soft deletion
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (parent_post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- we're gonna on conflict do nothing here
CREATE TABLE IF NOT EXISTS shadow_bans (
    userid BIGINT PRIMARY KEY
);

-- this table is to keep track of deletion of posts by moderators
CREATE TABLE IF NOT EXISTS moderation_actions (
    id SERIAL PRIMARY KEY,
    action VARCHAR(255) NOT NULL,
    target_user_id INTEGER NOT NULL,
    target_post_id INTEGER,
    performed_by INTEGER NOT NULL,
    reason VARCHAR(2048) DEFAULT 'No reason specified.',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    reverted_by INTEGER,
    reverted_at TIMESTAMP,

    FOREIGN KEY (performed_by) REFERENCES users(id),
    FOREIGN KEY (target_user_id) REFERENCES users(id),
    FOREIGN KEY (target_post_id) REFERENCES posts(id)
);