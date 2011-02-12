#from repoze.who.config import make_middleware_with_config
from elixir import metadata
#from config import config
import models as m
import cherrypy

def get_user_passwords():
    users = m.User.query.all()
    # later we can return dict which lookups from model
    data = dict(((u.handle,u.password) for u in users))
    return data

def hash_password(p):
    return m.User.create_password_hash(p)

def set_user():
    handle = cherrypy.request.login
    cherrypy.request.user = m.User.get_by(handle=handle)
