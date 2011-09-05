#!/usr/bin/python
import cherrypy
from cherrypy import wsgiserver
import sys, os
from auth import set_user
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
    # and for setting our user
    cherrypy.tools.set_user = cherrypy.Tool('before_handler', set_user)

    # set values on the request object for what section / subsection
    cherrypy.tools.set_section = cherrypy.Tool('before_handler', set_section)

    # get this thing hosted
    if 'production' in sys.argv:
        log.info('productin')
        config = './cherryconfig.production.ini'
    else:
        config = './cherryconfig.ini'

    # setup our ssl adapter
    cert_path = '/var/certs/server.crt'
    key_path = '/var/certs/server.key'
    ssl_adapter = wsgiserver.get_ssl_adapter_class()(cert_path, key_path)

    # update the server's config
    cherrypy.config.update(config)

    # create our app from root
    app = cherrypy.Application(c.Root())

    server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', 443), app)

    # associate the ssl adapter to the server
    server.ssl_adapter = ssl_adapter

    try:
        server.start()
    except:
        server.stop()
        raise
