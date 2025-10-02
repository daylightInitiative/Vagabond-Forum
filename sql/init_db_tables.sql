
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
-- also if you use a serial you dont need ON CONFLICT (tdid) DO NOTHING (or do something...?)
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
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    avatar_hash VARCHAR(32), -- the md5 hash of the avatar filename (we would get from the cdn but we dont have one)
    lastSeen TIMESTAMPTZ DEFAULT NOW(),
    join_date TIMESTAMPTZ DEFAULT NOW()
);
-- using TIMESTAMPZ to account for different timezones

CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    profile_id INT NOT NULL,
    FOREIGN KEY (profile_id) REFERENCES users(id),
    description VARCHAR(500) NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS temp_session_data (
    tempid SERIAL PRIMARY KEY,
    draft_text VARCHAR(2000) DEFAULT '' NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW()
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
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (temp_data_sid) REFERENCES temp_session_data(tempid)
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
    name VARCHAR(30) NOT NULL
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

