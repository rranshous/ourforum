from elixir import session, metadata, setup_all, DateTime
from elixir import Field, ManyToOne, OneToMany, Unicode
from restful.model import Entity

def reset_session():
    try:
        session.rollback()
        session.expunge_all()
        session.remove()
    except:
        pass
    return

def setup():
    metadata.bind = "sqlite:///./dbs/dev_rest.db"
    metadata.bind.echo = False
    setup_all()

class Feed(Entity):
    source = Field(Unicode)
    last_pulled = Field(DateTime)

    user = ManyToOne('User')
    posts = OneToMany('FeedPost')

class FeedPost(Entity):
    title = Field(Unicode)
    body = Field(Unicode)
    timestamp = Field(DateTime)

    feed = ManyToOne('Feed')
    comments = OneToMany('Comment')

class Comment(Entity):
    title = Field(Unicode)
    comment = Field(Unicode)

    post = ManyToOne('FeedPost')
    user = ManyToOne('User')

class User(Entity):
    handle = Field(Unicode)
    password_hash = Field(Unicode)

    comments = OneToMany('Comment')
    feeds = OneToMany('Feed')

