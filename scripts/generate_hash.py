import bcrypt
# 16 is enough entrophy but we want to be more secure
# utility for generating bcrypt hashes in setup phase

"""
    returns a bcrypt hash given a password and salt
"""
def create_hash(password: str) -> tuple[str, str]:
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(password.encode('utf-8'), salt)
    hash_str = hash.decode('utf-8')
    return hash_str, salt.decode('utf-8')

if __name__ == '__main__':
    try:

        raw_password = input("enter password: ")
        raw_salt = input("enter salt(press enter for random): ")
        #rand_salt = bcrypt.gensalt().decode('utf-8')

        if raw_salt == "":
            raw_salt = bcrypt.gensalt().decode('utf-8')

        hash, salt = create_hash(password=raw_password, salt=raw_salt)
        print("hash: ", hash, "salt: ", salt)

    except KeyboardInterrupt:
        print("Caught interrupt, exiting.")
    except Exception as e:
        print(f"Unknown error has occured: {e}")
