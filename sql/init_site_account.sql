INSERT INTO users (email, username, account_locked, is_online, hashed_password, password_salt, user_role)
    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
