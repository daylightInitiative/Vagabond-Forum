SELECT 
    p.*,
    COALESCE(rc.reply_count, 0) AS reply_count,
    u.username as author_username,
    COALESCE(gd.newest_post_date, NULL) AS newest_post_date
FROM (
    SELECT *
    FROM posts
    WHERE posts.category_id = %s
    ORDER BY creation_date DESC
    LIMIT %s OFFSET %s
) AS p
LEFT JOIN (
    SELECT parent_post_id, COUNT(*) AS reply_count
    FROM replies
    GROUP BY parent_post_id
) AS rc ON p.id = rc.parent_post_id
LEFT JOIN (
    SELECT MAX(creation_date) AS newest_post_date
    FROM posts
    WHERE posts.category_id = %s
) AS gd ON TRUE -- nothing to join on so we just put TRUE
LEFT JOIN users u ON u.id = p.author;