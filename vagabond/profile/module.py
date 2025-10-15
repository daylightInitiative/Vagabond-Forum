from vagabond.services import dbmanager as db

def create_profile(userID: str) -> None:

    # for now theres nothing tied to a profile but later there will be awards, titles and profile display settings
    db.write(query_str="""
        INSERT INTO profiles (profile_id)
            VALUES (%s)
    """, params=(userID,))