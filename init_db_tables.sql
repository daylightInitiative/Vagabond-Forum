
CREATE TABLE IF NOT EXISTS webstats (
    hits INT NOT NULL DEFAULT 0
);
INSERT INTO webstats (hits) VALUES (0);

CREATE TABLE IF NOT EXISTS users (
    userid SERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    username VARCHAR(20) UNIQUE NOT NULL CHECK (char_length(username) >= 3),
    hashed_password TEXT NOT NULL,
    ipaddr inet NOT NULL,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    join_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS news_feed (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    contents VARCHAR(5000) NOT NULL,
    author VARCHAR(20) NOT NULL,
    creation_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    views INT DEFAULT 0,
    contents VARCHAR(5000) NOT NULL,
    author VARCHAR(20) NOT NULL,
    creation_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS replies (
    id SERIAL PRIMARY KEY,
    parent_post_id INTEGER NOT NULL,
    contents VARCHAR(5000) NOT NULL,
    author VARCHAR(20) NOT NULL,
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (parent_post_id) REFERENCES posts(id) ON DELETE CASCADE
);