SELECT
    cn.*,
    COALESCE(pc.post_count, 0) AS post_count,
    COALESCE(rc.reply_count, 0) AS reply_count,
    COALESCE(pc.newest_post_date, NULL) AS newest_post_date -- cant reference it from its subquery or it oddly denotes as null without error
FROM categories AS cn
LEFT JOIN (
    SELECT category_id, MAX(creation_date) as newest_post_date, COUNT(*) AS post_count
    FROM posts
    GROUP BY category_id
) AS pc ON cn.id = pc.category_id
LEFT JOIN (
    SELECT posts.category_id, COUNT(replies.id) AS reply_count
    FROM replies
    JOIN posts ON replies.parent_post_id = posts.id
    GROUP BY posts.category_id
) AS rc ON cn.id = rc.category_id
ORDER BY cn.name ASC;