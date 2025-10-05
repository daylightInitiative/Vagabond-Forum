SELECT 
    p.*,
    COALESCE(rc.reply_count, 0) AS reply_count,
    u.username as author_username,
    COALESCE(gd.newest_post_date, NULL) AS newest_post_date
FROM (
    SELECT *
    FROM posts
    WHERE posts.category_id = %(category_id)s AND posts.deleted_at is NULL AND NOT EXISTS (
        SELECT 1 FROM shadow_bans
        WHERE userid = posts.author AND posts.author IS DISTINCT FROM %(current_userid)s
    ) -- when comparing null values use IS DISTINCT FROM
    ORDER BY creation_date DESC
    LIMIT %(page_limit)s OFFSET %(page_offset)s
) AS p
LEFT JOIN (
    SELECT parent_post_id, COUNT(*) AS reply_count
    FROM replies
    WHERE replies.deleted_at is NULL AND NOT EXISTS (
        SELECT 1 FROM shadow_bans
        WHERE userid = replies.author AND replies.author IS DISTINCT FROM %(current_userid)s
    )
    GROUP BY parent_post_id
) AS rc ON p.id = rc.parent_post_id
LEFT JOIN (
    SELECT MAX(creation_date) AS newest_post_date
    FROM posts
    WHERE posts.category_id = %(category_id)s and posts.deleted_at is NULL AND NOT EXISTS (
        SELECT 1 FROM shadow_bans
        WHERE userid = posts.author AND posts.author IS DISTINCT FROM %(current_userid)s
    )
) AS gd ON TRUE -- nothing to join on so we just put TRUE
LEFT JOIN users u ON u.id = p.author;