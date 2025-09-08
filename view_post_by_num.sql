SELECT json_agg(t.*)
FROM (
    SELECT * FROM posts
    WHERE id = %s
) AS t;