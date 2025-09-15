SELECT r.*, u.username AS author_username
FROM replies AS r
LEFT JOIN users u ON u.id = r.author
WHERE r.parent_post_id = %s
ORDER BY r.creation_date DESC;