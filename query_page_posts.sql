SELECT 
    p.*,
    COALESCE(rc.reply_count, 0) AS reply_count,
    u.username as author_username
FROM (
    SELECT *
    FROM posts
    ORDER BY creation_date DESC
    LIMIT %s OFFSET %s
) AS p
LEFT JOIN (
    SELECT parent_post_id, COUNT(*) AS reply_count
    FROM replies
    GROUP BY parent_post_id
) AS rc ON p.id = rc.parent_post_id
LEFT JOIN users u ON u.id = p.author;