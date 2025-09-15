SELECT p.*, u.username as author_username
FROM posts as p
LEFT JOIN users u ON u.id = p.author
WHERE p.id = %s