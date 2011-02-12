import cherrypy
from helpers import render, redirect

from lib.base import *

class Root(BaseController):
    """ sits @ The root of the app """

    @cherrypy.expose
    def public(self):
        return self.index()

    @cherrypy.expose
    def index(self):
        """ login if not authed else the home page """
        return render('/index.html')

    @cherrypy.expose
    def logout(self):
        """ clear the sesion to logout the user """
        cherrypy.lib.sessions.expire()
        redirect('/')

    @cherrypy.expose
    def contact(self):
        return render('/contact.html')
    contact_methods = contact
    contact_me = contact
