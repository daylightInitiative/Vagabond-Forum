INSERT INTO users (email, username, account_locked, is_online, hashed_password, ipaddr, is_superuser)
    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
