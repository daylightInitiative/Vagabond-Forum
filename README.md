# Vagabond Forum
Vagabond forum is a forum project written python using flask and postgresql as a RMDBS, with minimal dependencies

## Current Features:
- Categorized forums, with creator level and admin permissions
- Permission system for administrators and audit logs for moderation
- Forum credentials are stored in a `.env` file ignored by git and loaded at runtime
- Server sided session based system for login/signup and authentication
- Creation, deletion of posts and replies to posts globally by admins, and post/reply creators
- Browser fingerprinting for enhanced security and anonymous analytics
- Rich analytics and graphs for viewing frequency of `exitpages` and the duration of a viewing page to page, tracks what sites are in the `Referer` header
- Ability to invalidate all other sessions besides the current logged in one
- Saving of drafts during writing a new post automatically
- Public user profile page /users/USERID/ will display individual user info
- Dynamic creation of random pixelated patterns for default user avatars
- Soft deletion of posts  for further investigation, review etc