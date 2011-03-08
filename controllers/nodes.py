import cherrypy
from helpers import render, redirect
from json import dumps
from lib.base import *
from inspect import isclass

class Node(BaseController):
    """ server / edit / create nodes """

    def get_data(self,node_ids,depth=1):
        """ return back the json for the nodes,
            and their relative's possibly """

        to_return = {}

        # we can pass multiple nodes for the root lvl
        if not node_ids:
            return dumps({})

        # we'll take a string, if we have to
        if isinstance(node_ids,basestring):
            node_ids = map(int,node_ids.split(','))

        print 'node_ids: %s' % node_ids

        # for every lvl of depth we want
        # to return all the relating nodes
        # this could be alot quickly

        # recursion, recursion, recursion
        def _lvl(nodes,root_nodes,current_depth,depth):
            lvl = []
            cherrypy.log( 'nodes: %s' % [x.id for x in nodes])
            for node in nodes:
                o = node.json_obj()
                cherrypy.log('o: %s' % o)
                lvl.append(o)
                if current_depth < depth:
                    relatives = [x for x in node.relatives
                                       if x not in root_nodes]
                    print 'relatives: %s' % relatives
                    if relatives:
                        o['_relatives'] = _lvl(relatives,root_nodes,
                                               current_depth+1,depth)
            return lvl

        nodes = [m.Node.get(n) for n in node_ids]
        to_return = _lvl(nodes,nodes,1,depth)

        return to_return

    @cherrypy.expose
    def list(self,*args,**kwargs):
        return dumps(self.get_data(*args,**kwargs))

    @cherrypy.expose
    def get(self,*args,**kwargs):
        return dumps(self.get_data(*args,**kwargs)[0])

    @cherrypy.expose
    def update(self,**kwargs):
        # we are going to update an existing node
        # this can not involve changing it's type (right now)

        node = kwargs.get('id')
        if not node:
            error(404)

        # update the node from the kwargs
        updated = { }
        for k,v in kwargs:
            if k == 'id': continue
            if hasattr(node,k):
                setattr(node,k,v)
                updated[k] = node.get(v)

        # save our changes
        m.session.commit()

        # return the up to date representation
        return dumps(self.get_data([node.id]))

    @cherrypy.expose
    def create(self,**kwargs):
        # create a new node, get the node based on the type
        node_class = getattr(m,kwargs.get('type'))
        if not node_class:
            error(500,'wrong node class')

        # don't want to let through an id
        if 'id' in kwargs:
            del kwargs['id']

        # create our node
        node = node_class(**kwargs)
        m.session.commit()

        # return it's data
        return dumps(self.get_data([node.id]))


    ## helper methods !

    @cherrypy.expose
    def recent_nodes(self,count=10):
        ids =[i[0] for i in m.session.query(m.Node.id).limit(count).all()]
        return dumps(self.get_data(ids))

    @cherrypy.expose
    def describe(self,node_type=None,id=None):
        if id:
            node = m.Node.get(id)
            if not node:
                error(404)

            node_class = node.__class__

        else:
            node_class = getattr(m,node_type)
            if not node_class:
                error(404)

        fields = node_class._json_attribute_dict()

        return dumps(fields)

    @cherrypy.expose
    def get_types(self):
        """ returns possible node types """
        types = []
        for attr in dir(m):
            a = getattr(m,attr)

            # make sure it's a class
            if not isclass(a):
                continue

            # is it a json node?
            if issubclass(a,m.JsonNode) and a is not m.JsonNode:
                types.append(a.__name__)

        return dumps(types)
