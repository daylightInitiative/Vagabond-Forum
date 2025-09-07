DROP TABLE IF EXISTS webstats;
CREATE TABLE webstats (
    hits INT
);
INSERT INTO webstats (hits) VALUES (0);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    contents TEXT,
    author TEXT,
    creation_date TIMESTAMPTZ DEFAULT NOW()
);