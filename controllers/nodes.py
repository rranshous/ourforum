import cherrypy
import random
from helpers import render, redirect
from json import dumps, loads
from lib.base import *
from inspect import isclass
from decorator import decorator
from lib.memcache import default_client as memcache_client
from sqlalchemy import event
import zlib

# we want to make sure and listen on commits, if a commit
# happens we need to increment the memcache key counter
def increment_memcache_counter(*args,**kwargs):
    cherrypy.log('incrementing memcache')
    memcache_client.incr("key_counter")

# add the listener
event.listen(m.session, "after_commit", increment_memcache_counter)
# make sure the counter exists
r = memcache_client.get('key_counter')
if not r:
    memcache_client.set('key_counter',0)
else:
    memcache_client.incr('key_counter')


@decorator
def memcache(f, *args, **kwargs):
    # check if this set of args / kwargs / f is in memcache
    c = memcache_client.get('key_counter') or 0

    # create our key using function name and args
    key = '%s_%s_%s_%s' % (c,f.__name__,
                           '_'.join([str(x) for x in args
                                     if isinstance(x,(basestring,unicode))]),
                           '_'.join(['%s.%s' % (x,kwargs[x])
                                     for x in sorted(kwargs.keys())]))

    # fingers crossed
    cherrypy.log('memcache key: %s' % key)
    r = memcache_client.get(key)
    # miss =/
    if not r:
        r = f(*args,**kwargs)
        # update memcache
        cr = zlib.compress(r)
        cherrypy.log('writing compressed to memcache %s:%s'
                     % (len(r),len(cr)))
        memcache_client.set(key,cr)
    else:
        r = zlib.decompress(r)
        cherrypy.log('memcache hit')

    return r

class Node(BaseController):
    """ server / edit / create nodes """

    def get_data(self,node_ids,depth=1,show_repeats=False):
        """ return back the json for the nodes,
            and their relative's possibly """

        to_return = {}

        # make sure depth is an int
        depth = int(depth)

        # we can pass multiple nodes for the root lvl
        if not node_ids:
            return dumps({})

        # we'll take a string, if we have to
        if isinstance(node_ids,basestring):
            node_ids = map(int,node_ids.split(','))

        print 'node_ids: %s' % node_ids
        print 'depth: %s' % depth

        # for every lvl of depth we want
        # to return all the relating nodes
        # this could be alot quickly

        # recursion, recursion, recursion
        def _lvl(nodes,root_nodes,current_depth,depth,previous_nodes=[]):
            lvl = []

            # nothing to see here
            if not nodes:
                return lvl

            for node in nodes:
                o = node.json_obj()
                lvl.append(o)
                relatives = node.relatives
                # don't wanna go a > b > a
                relatives = [r for r in relatives
                             if not r in previous_nodes or isinstance(r,m.Author)]
                if current_depth < depth:
                    # if we are not skipping we filter out nodes from the root
                    # except users of course
                    if not show_repeats:
                        relatives = [x for x in node.relatives
                                     if x not in root_nodes or
                                     isinstance(x,m.Author)]
                    if relatives:
                        o['_relatives'] = _lvl(relatives,root_nodes,
                                               current_depth+1,depth,
                                               nodes)

                # if this isn't a user node, fill in it's author
                elif not isinstance(node,m.Author):
                    author = node.get_author()
                    if author:
                        o['_relatives'] = [author.json_obj()]
                    else:
                        cherrypy.log('No Author!: %s' % node.id)

            return lvl

        nodes = [m.Node.get(n) for n in node_ids]
        to_return = _lvl(nodes,nodes,1,depth)

        return to_return

    @cherrypy.expose
    @memcache
    def list(self,node_ids,depth=1):
        return dumps(self.get_data(node_ids,depth))

    @cherrypy.expose
    @memcache
    def get(self,node_id,depth=1):
        return dumps(self.get_data(node_id,depth)[0])

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
        return dumps(self.get_data([node.id]))

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
        return dumps(self.get_data([node.id])[0])


    ## helper methods !

    @cherrypy.expose
    @memcache
    def recent(self,count=10,depth=1):
        # order the nodes so that the most recently updated ones are first
        # followed by those who most recently had a relative updated
        query = m.Node.query.order_by(m.Node.updated_at.desc(),
                                      m.Node.relative_updated_at.desc(),
                                      m.Node.id.desc())

        # limit to our count
        query = query.limit(count * 2)

        # the front page should not have authors or users
        # TODO: in query
        nodes = query.all()
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

        return dumps(self.get_data(ids,depth,show_repeats=True))

    @cherrypy.expose
    @memcache
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
    @memcache
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
    @memcache
    def search(self,s):
        """ search for a node """

        # keepin it simple for now
        found = []

        cherrypy.log('search: %s' % s)

        # one keyword one value
        if ':' in s:
            cherrypy.log('k/v search')
            k,v = s.split(':')
            if k.lower() == 'type':
                cls = getattr(m,v)
                if cls:
                    found += cls.query.all()
            found += m.JsonNode.get_bys(k=v)
        else:
            log.debug('general search')
            # general search
            found += m.Node.query.filter(m.JsonNode.data.like('%'+s+'%')).all()

        cherrypy.log('found: %s' % found)

        return self.list([x.id for x in set(found)])


    @cherrypy.expose
    def save_down(self,id):
        """ save the node's content to the disk """

        node = m.Node.get(id)

        if not node:
            error(400)

        node.save_down()

