
CREATE TABLE IF NOT EXISTS webstats (
    hits INT
);
INSERT INTO webstats (hits) VALUES (0);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title TEXT,
    contents TEXT,
    author TEXT,
    creation_date TIMESTAMPTZ DEFAULT NOW()
);