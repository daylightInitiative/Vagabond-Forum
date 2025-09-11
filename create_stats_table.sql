
CREATE TABLE IF NOT EXISTS webstats (
    hits INT
);
INSERT INTO webstats (hits) VALUES (0);

CREATE TABLE IF NOT EXISTS news_feed (
    id SERIAL PRIMARY KEY,
    title TEXT,
    pinned BOOLEAN,
    contents TEXT,
    author TEXT,
    creation_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title TEXT,
    views INT DEFAULT 0,
    contents TEXT,
    author TEXT,
    creation_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS replies (
    id SERIAL PRIMARY KEY,
    parent_post_id INTEGER,
    contents TEXT,
    author TEXT,
    creation_date TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (parent_post_id) REFERENCES posts(id) ON DELETE CASCADE
);