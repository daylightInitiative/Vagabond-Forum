SELECT * FROM news_feed
    WHERE NOT pinned
    ORDER BY creation_date DESC