import cherrypy
import random
from helpers import (render, redirect, get_node_data, memcache_cache,
                     node_most_recent_relative_update)
from json import dumps, loads
from lib.base import *
from inspect import isclass
from decorator import decorator
import zlib


class Node(BaseController):
    """ server / edit / create nodes """


    @cherrypy.expose
    @memcache_cache
    def list(self,node_ids,depth=1):
        return dumps(get_node_data(node_ids,depth))

    @cherrypy.expose
    @memcache_cache
    def get(self,node_id,depth=1):
        return dumps(get_node_data(node_id,depth)[0])

    def _modify_relative(self,node,relative,m_add=False,m_remove=False):
        print 'modifying relative: %s' % relative.id
        if relative:
            if m_add:
                print 'adding'
                node.relatives.append(relative)
                relative.relatives.append(node) # doing both sides
            if m_remove:
                try:
                    print 'removing'
                    node.relatives.remove(relative)
                    relative.relatives.remove(node)
                except:
                    # guess they aren't related
                    pass

    def _modify_relatives(self,node,relative_ids,m_add=False,m_remove=False):
        print 'modifying relatives'
        if not m_add and not m_remove:
            return

        if iterable(relative_ids):
            print 'iterable'
            for node_id in relative_ids:
                relative = m.Node.get(node_id)
                self._modify_relative(node,relative,m_add,m_remove)
        else:
            print 'not iterable'
            relative = m.Node.get(relative_ids)
            self._modify_relative(node,relative.m_add,m_remove)


    @cherrypy.expose
    def update(self,**kwargs):
        # we are going to update an existing node
        # this can not involve changing it's type (right now)

        node = m.Node.get(kwargs.get('id'))
        if not node:
            error(404)

        # update the node from the kwargs
        for k,v in kwargs.iteritems():
            if k == 'id': continue
            if hasattr(node,k):
                setattr(node,k,v)

        # see if there are any more tasks
        if '_add_relative' in kwargs:
            cherrypy.log('adding relative: %s' % kwargs.get('_add_relative'))
            to_add = m.Node.get(kwargs.get('_add_relative'))
            self._modify_relative(node,to_add,m_add=True)

        if '_remove_relative' in kwargs:
            to_remove = m.Node.get(kwargs.get('_remove_relative'))
            self._modify_relative(node,to_remove,m_remove=True)

        # save our changes
        m.session.commit()

        # return the up to date representation
        return dumps(get_node_data([node.id]))

    @cherrypy.expose
    def create(self,**kwargs):
        # create a new node, get the node based on the type
        cherrypy.log('type: %s' % kwargs.get('type'))
        node_class = getattr(m,kwargs.get('type'))
        if not node_class:
            error(500,'wrong node class')

        # don't want to let through an id
        if 'id' in kwargs:
            del kwargs['id']

        # create our node
        node = node_class(**kwargs)
        cherrypy.log('node: %s')

        # add the current user as a relative for creating it
        self._modify_relative(node,get_user().get_author(),m_add=True)

        # see if it has any relatives
        if '_add_relative' in kwargs:
            cherrypy.log('adding relative: %s' % kwargs.get('_add_relative'))
            to_add = m.Node.get(kwargs.get('_add_relative'))
            self._modify_relative(node,to_add,m_add=True)


        # commit that shit!
        m.session.commit()

        # return it's data
        return dumps(get_node_data([node.id])[0])


    ## helper methods !

    @cherrypy.expose
    @memcache_cache
    def describe(self,node_type=None,id=None):
        # return back a description of the nodes
        # type's fields

        # if they passed an id, than get it's type
        if id:
            node = m.Node.get(id)
            if not node:
                error(404)

            node_class = node.__class__

        else:
            node_class = getattr(m,node_type)
            if not node_class:
                error(404)

        # get the fields from the node type
        fields = node_class._json_attribute_dict()

        # we want to include properties
        for attr in dir(node_class):
            prop = getattr(node_class,attr)
            if isinstance(prop,property) and prop.fset:
                fields[attr] = 'str'

        # TODO: not make as hackish
        if m.User == node_class:
            del fields['password_hash']

        # add in our type
        return dumps({'fields':fields,'type':node_class.__name__})


    @cherrypy.expose
    @memcache_cache
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


    @cherrypy.expose
    def save_down(self,id):
        """ save the node's content to the disk """

        node = m.Node.get(id)

        if not node:
            error(400)

        node.save_down()

