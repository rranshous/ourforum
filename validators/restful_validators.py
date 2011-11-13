from formencode import Schema, validators as v

v.UnicodeString

class Feed(Schema):
    source = v.URL(not_empty=True)
    last_pulled = v.DateConverter(
                    if_missing=None,
                    month_style='dd/mm/yyyy')

    #user
    posts = v.Set()

class FeedPost(Schema):
    title = v.UnicodeString(not_empty=True)
    body = v.UnicodeString(not_empty=True)
    timestamp = v.DateConverter(
                    if_missing=None,
                    month_style='dd/mm/yyyy')
    #feed
    comments = v.Set()

class Comment(Schema):
    title = v.UnicodeString()
    comment = v.UnicodeString()

    #post
    #user

class User(Schema):
    handle = v.UnicodeString()
    password_hash = v.UnicodeString()

    comments = v.Set()
    feeds = v.Set()
