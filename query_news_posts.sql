SELECT json_agg(sub.*)
FROM (
    SELECT *
        FROM news_feed
        WHERE NOT pinned
        ORDER BY creation_date DESC
) AS sub;