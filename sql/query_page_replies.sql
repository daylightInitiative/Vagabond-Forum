SELECT r.*, u.username AS author_username
FROM replies AS r
LEFT JOIN users u ON u.id = r.author
WHERE r.parent_post_id = %s AND r.deleted_at IS NULL AND NOT EXISTS (
    SELECT 1 FROM shadow_bans
    WHERE userid = r.author AND r.author != %s
)
ORDER BY r.creation_date DESC;