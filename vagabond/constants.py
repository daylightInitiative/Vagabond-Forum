
MAX_URL_TITLE = 40
FORUM_PAGE_LIMIT = 10
MESSAGE_PAGE_LIMIT = 65

SYSTEM_ACCOUNT_ID = "1"

from enum import Enum, auto, StrEnum
# errors (consistency is important with our api)

class UserRole(StrEnum):
    USER = "user"               # normal registered user
    MODERATOR = "moderator"     # forum moderator
    ADMIN = "admin"             # site admins who moderate, well..moderators

class PostType(Enum):

    MESSAGE = "user_messages"
    REPLY = "replies"
    POST = "posts"

# these actions can also be performed by a special user named "SYSTEM" which is automated
# TODO: move over ban data to another table specifically for it
class ModerationAction(Enum):
    BAN_USER = 'ban_user'
    UNBAN_USER = 'unban_user'
    SHADOWBAN_USER = 'shadowban_user' # i see no upside of adding a "unshadowban" if you have this, you've earned it
    MUTE_USER = 'mute_user'
    UNMUTE_USER = 'unmute_user'
    DELETE_POST = 'delete_post'
    UNDELETE_POST = 'undelete_post'
    DELETE_MESSAGE = 'delete_message' # direct messaging logging
    DELETE_GROUP = 'delete_group' # delete group direct message
    EDIT_MESSAGE = 'edit_message' # edit direct message
    DELETE_REPLY = 'delete_reply' # undeleting a reply also seems kind of useless
    WARN_USER = 'warn_user'
    EDIT_POST = 'edit_post'
    LOCK_POST = 'lock_post'
    PIN_POST = 'pin_post'
    CHANGE_USERNAME = 'change_username'
    CHANGE_ROLE = 'change_role'
    SUSPEND_USER = 'suspend_user'
    ENABLE_2FA = 'enable_2fa'
    DISABLE_2FA = 'disable_2fa'
    REVERT_ACTION = 'revert_action'

# later we can localize these constants with a translator function
class SuccessMessage(Enum):
    CREATED_TICKET = 'Created new ticket'
    CREATED_NEW_GROUP = 'Created new group'
    CREATED_MESSAGE = 'Created group message'
    CHANGED_GROUP_OWNER = 'Changed group owner'
    SENT_VERIFICATION_CODE = 'Sent verification code to email'
    SIGNED_OUT_ALL_SESSIONS = 'Signed out of all other sessions'
    SAVED_ANALYTICS = 'Saved analytics'
    DELETED_MESSAGE = 'Deleted message'
    DELETED_GROUP = 'Deleted group'
    SAVED_DRAFT_DATA = 'Saved draft data'
    EDITED_MESSAGE = 'Edited message'
    COMPLETED_MODACTION = 'Completed moderation action'

class RouteError(Enum):

    INVALID_FORM_DATA = "Invalid form data"
    INVALID_CATEGORY_ID = "Invalid category ID"
    INVALID_POST_ID = "Invalid post ID"
    INVALID_PAGE_ID = "Invalid page ID"
    INVALID_USER_ID = "Invalid user ID"
    INVALID_REQUEST = "Invalid request"
    INVALID_SESSION = "Invalid session"


    INVALID_PERMISSIONS = "Invalid permissions"
    BAD_TOKEN = "Bad token"
    EXPIRED_TOKEN = "Expired token"
    INTERNAL_SERVER_ERROR = "Internal Server Error"
    FETCH_NO_CONTENT = "Fetch returned no content"

    # eventually they will all be unionized to use jsonify and its appropriate error code
    REQUEST_SUCCESS = "Success"
