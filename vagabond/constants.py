
MAX_URL_TITLE = 40
PAGE_LIMIT = 10

import json
from flask import jsonify
from enum import Enum, auto
# errors (consistency is important with our api)

class RouteStatus(Enum):

    INVALID_FORM_DATA = "Invalid form data"
    INVALID_CATEGORY_ID = "Invalid category ID"
    INVALID_POST_ID = "Invalid post ID"
    INVALID_PAGE_ID = "Invalid page ID"
    INVALID_USER_ID = "Invalid user ID"
    INVALID_REQUEST = "Invalid request"


    INVALID_PERMISSIONS = "Invalid permissions"
    BAD_TOKEN = "Bad token"
    EXPIRED_TOKEN = "Expired token"
    INTERNAL_SERVER_ERROR = "Internal Server Error"
    FETCH_NO_CONTENT = "Fetch returned no content"

    # eventually they will all be unionized to use jsonify and its appropriate error code
    REQUEST_SUCCESS = "Success"
