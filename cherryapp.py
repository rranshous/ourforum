#!/usr/bin/python
import cherrypy
import sys
from auth import set_user
from helpers import set_section
import logging as log
import models as m
import controllers as c


if __name__ == "__main__":
    # setup the db connection
    m.setup()

    # create our app from root
    app = cherrypy.Application(c.Root())

    # setup a tool to rset our db session
    cherrypy.tools.reset_db = cherrypy.Tool('on_end_resource',
                                            m.reset_session)

    # validates a user is logged in
    cherrypy.tools.check_active_login = cherrypy.Tool('before_handler',
                                                      check_active_login,
                                                      priority = 10)

    # setting our user from session data
    cherrypy.tools.set_user = cherrypy.Tool('before_handler', set_user)

    # set values on the request object for what section / subsection
    cherrypy.tools.set_section = cherrypy.Tool('before_handler', set_section)

    # get this thing hosted
    if 'production' in sys.argv:
        config = 'cherryconfig.production.ini'
    else:
        config = './cherryconfig.ini'
        cherrypy.quickstart(app, config=config)

