import cherrypy
import random
from helpers import (render, redirect, get_node_data, memcache_cache,
                     node_most_recent_relative_update)
from lib.base import *
from inspect import isclass
from decorator import decorator
from json import dumps, loads


class View(BaseController):

    @cherrypy.expose
    @memcache_cache
    def root_comments(self):
        """ like search for comment nodes but does
            not pick up comment nodes which are related
            to a feed node """
        pass

    @cherrypy.expose
    @memcache_cache
    def search(self,s):
        """ search for a node """

        # keepin it simple for now
        found = []

        cherrypy.log('search: %s' % s)

        # one keyword one value
        if ':' in s:
            for k,v in [x.split(':') for x in s.split()]:
                cherrypy.log('k/v search')
                if k.lower() == 'type':
                    cls = getattr(m,v)
                    if cls:
                        found += cls.query.order_by(cls.id.desc()).all()
                else:
                    found += m.JsonNode.get_bys(k=v)
        else:
            cherrypy.log('general search')
            # general search
            found += m.Node.query.filter(m.JsonNode.data.like('%'+s+'%')). \
                     order_by(m.JsonNode.updated_at.desc(),
                              m.JsonNode.id.desc()).all()

        return cherrypy.root.node.list([x.id for x in found])


    @cherrypy.expose
    @memcache_cache
    def recent(self,count=10,depth=1,node_type='Node'):
        # order the nodes so that the most recently updated ones are first
        # followed by those who most recently had a relative updated
        cls = getattr(m,node_type,m.Node)
        query = cls.query.order_by(m.Node.updated_at.desc(),
                                   m.Node.relative_updated_at.desc(),
                                   m.Node.id.desc())

        # limit to our count
        query = query.limit(count * 2)

        # the front page should not have authors or users
        # TODO: in query
        nodes = query.all()

        # if we aren't filtering on node type, filter out some things
        if cls is m.Node:
            filter_types = (m.User,m.Author,m.SexyLady)
            nodes = [n for n in nodes if not isinstance(n,filter_types)]

        # make sure depth is a #
        depth = int(depth)

        # we want to order these such that the newest nodes appear first
        # but if a node relative (comment) was added to a name
        # than we want to show the node the comment was added to
        # but not the comment itself @ root (make sense?)

        # reverse to work backwards
        rev_nodes = nodes[::-1]
        seen = []
        for node in rev_nodes:
            # since we are working backwards, any node which
            # was already a relative that we've seen should be skipped
            if node in seen:
                nodes.remove(node)
            else:
                rels = node.get_relatives(depth)
                seen += rels

        # pull the id's off the returned tuple
        ids = [i.id for i in nodes][:int(count)]

        # get dicts of data
        data = get_node_data(ids,depth,show_repeats=True)

        # sort the data by most recently updated relative
        # I know this is attrocious. should be doing this
        # in sql
        data.sort(key=node_most_recent_relative_update)

        return dumps(data)

