import bcrypt
# 16 is enough entrophy but we want to be more secure
#https://argon2-cffi.readthedocs.io/en/stable/howto.html
# utility for generating argon hashes quickly

try:

    raw_password = input("enter password: ").encode('utf-8') # bytes
    rand_salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(raw_password, rand_salt)
    print("hash: ", hash.decode('utf-8'), "salt: ", rand_salt.decode('utf-8'))

except KeyboardInterrupt:
    print("Caught interrupt, exiting.")
except Exception as e:
    print(f"Unknown error has occured: {e}")
