INSERT INTO users (email, username, account_locked, is_online, hashed_password, password_salt, is_superuser)
    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
