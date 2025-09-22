SELECT 
    nf.title,
    nf.contents,
    nf.pinned,
    nf.creation_date,
    u.username AS author_username
FROM news_feed nf
LEFT JOIN users u ON u.id = nf.author
WHERE NOT nf.pinned
ORDER BY nf.creation_date DESC;