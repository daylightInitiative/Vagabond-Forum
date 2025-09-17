
CREATE TABLE IF NOT EXISTS webstats (
    hits INT NOT NULL DEFAULT 0
);
INSERT INTO webstats (hits) VALUES (0);


CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(20) UNIQUE NOT NULL CHECK (char_length(username) >= 3),
    account_locked BOOLEAN NOT NULL DEFAULT FALSE,
    loginAttempts int NOT NULL DEFAULT 0,
    is_online BOOLEAN NOT NULL DEFAULT FALSE,
    hashed_password VARCHAR(255) NOT NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    lastSeen TIMESTAMPTZ DEFAULT NOW(),
    join_date TIMESTAMPTZ DEFAULT NOW()
);
-- using TIMESTAMPZ to account for different timezones

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
    temp_data_sid INT NOT NULL,
    lastLogin TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (temp_data_sid) REFERENCES temp_session_data(tempid)
);

CREATE TABLE IF NOT EXISTS news_feed (
    id SERIAL PRIMARY KEY,
    title VARCHAR(250) NOT NULL,
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    contents VARCHAR(2000) NOT NULL,
    author BIGINT NOT NULL REFERENCES users (id),
    creation_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(250) NOT NULL,
    views INT DEFAULT 0,
    contents VARCHAR(2000) NOT NULL,
    author BIGINT NOT NULL REFERENCES users (id),
    creation_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS replies (
    id SERIAL PRIMARY KEY,
    parent_post_id INTEGER NOT NULL,
    contents VARCHAR(500) NOT NULL,
    author BIGINT NOT NULL REFERENCES users (id),
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (parent_post_id) REFERENCES posts(id) ON DELETE CASCADE
);

