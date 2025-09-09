SELECT json_agg(sub.*)
FROM (
    SELECT * FROM replies WHERE parent_post_id = %s
    ORDER BY creation_date DESC
) AS sub;