from templates import render
from sqlalchemy import event
from json import dumps, loads
import cherrypy
from cherrypy import HTTPRedirect, HTTPError
from decorator import decorator
import models as m
from lib.memcache import default_client as memcache_client
import zlib



def error(*args):
    raise HTTPError(*args)

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

def iterable(o):
    try:
        i = iter(o)
        return True
    except TypeError:
        return False


def get_node_data(node_ids,depth=1,show_repeats=False):
    """ return back the json for the nodes,
        and their relative's possibly """

    # make sure depth is an int
    depth = int(depth)

    # we can pass multiple nodes for the root lvl
    if not node_ids:
        return []

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
            if current_depth < depth and not isinstance(node,m.Author):
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

        return lvl

    nodes = [m.Node.get(n) for n in node_ids]
    to_return = _lvl(nodes,nodes,1,depth)

    return to_return


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

def node_most_recent_relative_update(node_datas):
    # go down through the relatives, find the newest one
    def c(nds):
        newest = nds.get('epoch_updated_at')
        for node_data in nds.get('_relatives',[]):
            f = c(node_data)
            if f > newest:
                newest = f
        return newest
    newest = c(node_datas)
    return -newest

@decorator
def memcache_cache(f, *args, **kwargs):
    # check if this set of args / kwargs / f is in memcache
    c = memcache_client.get('key_counter') or 0

    # create our key using function name and args
    key = '%s_%s_%s_%s' % (c,f.__name__,
                           '_'.join([str(x) for x in args
                                     if isinstance(x,(basestring,unicode))]),
                           '_'.join(['%s.%s' % (x,kwargs[x])
                                     for x in sorted(kwargs.keys())]))

    key = key.replace(' ','')

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

