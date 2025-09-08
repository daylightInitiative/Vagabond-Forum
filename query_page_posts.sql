SELECT json_agg(sub.*)
FROM (
    SELECT * FROM posts
    ORDER BY creation_date DESC
    LIMIT 10 OFFSET %s
) AS sub;