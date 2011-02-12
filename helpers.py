from templates import render
import cherrypy
from cherrypy import HTTPRedirect, HTTPError
from decorator import decorator

@decorator
def require_admin(f,*args,**kwargs):
    """ raises 403 if user is not an admin """
    if not cherrypy.request.user.is_admin:
        raise HTTPError(403)
    return f(*args,**kwargs)

def add_flash(msg_type,msg=None):
    if not msg:
        msg = msg_type
        msg_type = 'info'

    cherrypy.session.setdefault(msg_type,[]).append(msg)

def redirect(*args,**kwargs):
    raise HTTPRedirect(*args,**kwargs)

def set_section():
    pieces = cherrypy.request.path_info.split('/')
    cherrypy.request.section_name = pieces[1]
    cherrypy.log('section_name: %s' % pieces[1])
    if len(pieces) > 2:
        cherrypy.request.subsection_name = pieces[2]
    else:
        cherrypy.request.subsection_name = ''

def is_active_section(s):
    return cherrypy.request.section_name == s

def is_active_subsection(s):
    return cherrypy.request.subsection_name == s
