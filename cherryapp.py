#!/usr/bin/python
import cherrypy
from cherrypy import wsgiserver
import sys, os
from auth import set_user, check_active_login
from helpers import set_section
import logging
import models as m
import controllers as c

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler(sys.stdout))

if __name__ == "__main__":
    log.info('starting')

    # setup the db connection
    m.setup()

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
        log.info('productin')
        config = './cherryconfig.production.ini'

        # setup our ssl adapter
        cert_path = '/var/certs/server.crt'
        key_path = '/var/certs/server.key'
        ssl_adapter = wsgiserver.get_ssl_adapter_class()(cert_path, key_path)

        # update the server's config
        cherrypy.config.update(config)

        # create our app from root
        app = cherrypy.Application(c.Root(),config=config)

        # TODO: not hardcode
        server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', 443), app)

        if 'production' in sys.argv:
            # associate the ssl adapter to the server
            server.ssl_adapter = ssl_adapter

        # we're probably root, lets switch to our www-data user/group
        # TODO: not hardcode
        server.uid = 33
        server.gid = 33

        try:
            server.start()
        except:
            server.stop()
            raise

    else:
        config = './cherryconfig.ini'
        # create our app from root
        app = cherrypy.Application(c.Root(),config=config)
        cherrypy.quickstart(app,config=config)


