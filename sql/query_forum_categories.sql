SELECT
    cn.*,
    COALESCE(rc.reply_count, 0) AS reply_count,
    COALESCE(post_count, 0) AS post_count
FROM (
    SELECT posts.id, posts.category_id, COUNT(*) as post_count
    FROM posts
    GROUP BY posts.id
) AS pc
LEFT JOIN (
    SELECT *
    FROM categories
    ORDER BY name ASC
) AS cn ON pc.category_id = cn.id
LEFT JOIN (
    SELECT parent_post_id, COUNT(*) AS reply_count
    FROM replies
    GROUP BY parent_post_id
) AS rc ON pc.id = rc.parent_post_id