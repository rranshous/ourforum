import cherrypy
from helpers import render, redirect
from json import dumps
from lib.base import *

class Root(BaseController):
    """ sits @ The root of the app """

    @cherrypy.expose
    def get_nodes_data(self,node_ids,depth=1):
        """ return back the json for the node,
            and it's relative's possibly """

        to_return = {}

        # we can pass multiple nodes for the root lvl
        node_ids = map(int,node_ids.split(','))

        print 'node_ids: %s' % node_ids

        # for every lvl of depth we want
        # to return all the relating nodes
        # this could be alot quickly

        # recursion, recursion, recursion
        def _lvl(nodes,root_nodes,current_depth,depth):
            lvl = []
            for node in nodes:
                o = node.json_obj()
                print 'o: %s' % o
                lvl.append(o)
                if current_depth < depth:
                    relatives = [x for x in node.relatives
                                       if x not in root_nodes]
                    o['_relatives'] = _lvl(relatives,root_nodes,
                                           current_depth+1,depth)
            return lvl

        nodes = [m.Node.get(n) for n in node_ids]
        print 'nodes: %s' % nodes
        to_return = _lvl(nodes,nodes,1,depth)

        return to_return

    @cherrypy.expose
    def nodes(self,ids,depth=1):
        return dumps(self.get_nodes_data(ids,depth=depth))

    @cherrypy.expose
    def node(self,ids):
        return dumps(self.get_nodes_data(ids)[0])

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
