from elixir import *
import datetime
import cherrypy
from hashlib import sha1
import models as m
import os
import random
from json import dumps, loads
from urllib2 import urlopen
from helpers import render


TYPE_LOOKUP = {'unicode':'str',
               'None':'str'}

## helper functions ##
def add_tag_by_name(self,name):
    tag = Tag.get_by(name=name)
    if not tag:
        tag = Tag(name=name)
        session.add(tag)
    if tag not in self.tags:
        self.tags.append(tag)

def reset_session():
    try:
        session.rollback()
        session.expunge_all()
        session.remove()
    except:
        pass
    return

def setup():
    metadata.bind = "sqlite:///./dbs/dev.db"
    metadata.bind.echo = False
    setup_all()



## end helper functions ##

# for now
BaseEntity = Entity

class SetHookDict(dict):
    def call_callback(self):
        if hasattr(self,'callback'):
            self.callback(self)

    def __setitem__(self,*args):
        super(SetHookDict,self).__setitem__(*args)
        self.call_callback()

    def __delitem__(self,*args):
        super(SetHookDict,self).__delitem__(*args)
        self.call_callback()

    def update(self,*args):
        super(SetHookDict,self).update(*args)
        self.call_callback()

class JsonAttribute:
    """
    can be set on a JsonNode to represent
    a default attr:value which will be set on init
    """
    def __init__(self,default=None):
        self.default = default

class Node(BaseEntity):
    """
    A node is a single information unit
    """

    # our data field will hold all the data for this node
    data = Field(UnicodeText)

    # nodes can relate to eachother many to many
    relatives = ManyToMany('Node', tablename='relationships')

    # when we we created / updated ?
    created_at = Field(TIMESTAMP)
    updated_at = Field(DATETIME)

    # for sorting we want to know when a relation updated last
    relative_updated_at = Field(DATETIME)


class JsonNode(Node):
    """
    The data we contain is going to be a json object.
    data = {
        'attr':'value',
        'attr2':'value',
    }
    we are going to setup this entity so that
    attribute attempts will be backed by the json obj

    we are relying on sqlalchemy to do the heavy lifting
    """

    save_base = './saved_data/'

    def __init__(self,*args,**kwargs):
        """
        setup attributes in the json data for our
        JsonAttribute's as well as the kwargs
        """

        # call our super
        super(JsonNode,self).__init__(*args,**kwargs)

        # get our data, this will be blank
        # but the data obj will set the value
        # against the entities json data
        # when u set the value in the data obj
        data = self._get_json_data()

        # update our data dict w/ the base
        # attributes
        for k,v in vars(self).iteritems():
            if isinstance(v,JsonAttribute):
                data[k] = v.default

        # update from our kwargs
        for k,v in kwargs.iteritems():
            setattr(self,k,v)

    @classmethod
    def get_by(cls,**kwargs):
        """
        over ride to provide compatibility,
        shitty list look through
        """
        for o in cls.query.all():
            count = 0
            for k,v in kwargs.iteritems():
                o_v = getattr(o,k)
                if o_v == v:
                    count += 1
            if count == len(kwargs):
                return o
        return None

    @classmethod
    def get_bys(cls,**kwargs):
        """
        like get_by for returns list
        """

        # we are going to search the json data for substrings
        subs = []
        filters = []
        query = cls.query
        for k,v in kwargs.iteritems():
            s = dumps({k:v})[2:-2]
            # they want a like
            print 's: %s' % s
            query = query.filter(getattr(cls,'data').like('%'+v+'%'))
        return query.all()

    def _update_default_data(self):
        """ since we can't set our data on init we
            are going to have to set it after """

        if self.defaulted:
            return False

        data = {}

        # update our data string
        self._update_json(data)

        # update our flag
        self.defaulted = True

    def _is_json_attribute(self,attr):
        try:
            value = self.__getattribute__(attr,bypass=True)
        except AttributeError:
            return False

        if isinstance(value,JsonAttribute):
            return True

        return False

    @classmethod
    def _json_attribute_dict(cls):
        """ returns a dict w/ json attributes
            and the value types """

        global TYPE_LOOKUP

        fields = {}

        for attr in dir(cls):
            v = getattr(cls,attr)
            if isinstance(v,JsonAttribute):
                t = type(v.default).__name__
                if t in TYPE_LOOKUP:
                    t = TYPE_LOOKUP[t]
                fields[attr] = t

        return fields

    def __getattribute__(self,attr,**kwargs):
        """
        check our json data for the info.
        If they are trying to get a JsonAttribute
        than we use the json data
        """

        # lets see what the value of this is,
        # if it's a JsonAttribute than we are going
        # to ref json data
        value = super(JsonNode,self).__getattribute__(attr)
        if isinstance(value,JsonAttribute) and not kwargs.get('bypass'):
            data = self._get_json_data()
            if attr in data:
                return data.get(attr)
            else:
                return value.default

        return value

    def __setattr__(self,attr,value):
        """ update our json data """
        if self._is_json_attribute(attr):
            data = self._get_json_data()
            data[attr] = value
            return True
        return super(JsonNode,self).__setattr__(attr,value)

    def _get_json_data(self):
        """
        return the obj from json. the dict
        returned is special in that it will re-write
        the json string to the data attr on each update
        """

        if self.data:
            data = SetHookDict(loads(self.data))
            data.callback = self._update_json
            return data
        d = SetHookDict()
        d.callback = self._update_json
        return d

    def _update_json(self,data):
        """ update the data attribute w/ json for passed data """
        self.data = dumps(data)
        # update our time stamp
        now = datetime.datetime.now()
        self.updated_at = now
        # update our relatives
        for r in self.relatives:
            r.relative_updated_at = now

    @staticmethod
    def _json_obj(node):
        if node.data:
            o = loads(node.data)
        else:
            o = {}
        o['id'] = node.id
        o['type'] = node.__class__.__name__
        return o

    def json_obj(self):
        """
        returns the python dict
        for the json obj
        """
        return self._json_obj(self)

    def save_down(self):
        """ saves a copy of our data to the disk """
        raise NotImplemented

    def get_author(self):
        """ if there is an author node related to this
            return it or None """
        authors = [a for a in self.relatives if isinstance(a,m.Author)]
        if authors:
            return authors[0]
        return None

class FeedEntry(JsonNode):
    """
    a node based off an RSS feed entry
    """

    source = JsonAttribute('')
    title = JsonAttribute('')
    body = JsonAttribute('')
    timestamp = JsonAttribute('')

    def save_down(self):
        """ save down the body as a html file """
        html = render('/feedentrysavedown.html',
                      source=self.source,
                      title=self.title,
                      body=self.body,
                      timestamp=self.timestamp)
        title = self.title.replace(os.sep,'')
        path = os.path.join(self.save_base,
                            self.__class__.__name__,
                            '%s(%s).html'%(title,self.id))
        print 'saving: %s' % path
        with open(path,'w') as fh:
            fh.write(html)

        return path


class Comment(JsonNode):
    """
    a comment probably entered through the site
    """

    title = JsonAttribute('')
    comment = JsonAttribute('')

    def save_down(self):
        """ save down a txt file """
        html = render('/commentsavedown.txt',
                      title=self.title,
                      comment=self.comment,
                      author=self.get_author().get_user().handle)
        name = (self.title or self.comment).replace(os.sep,'')
        path = os.path.join(self.save_base,
                            self.__class__.__name__,
                            '%s_(%s).html'%(name,self.id))
        print 'saving: %s' % path
        with open(path,'w') as fh:
            fh.write(html)
        return path


class User(JsonNode):
    """
    The user node will hold info about the users.
    """

    handle = JsonAttribute('')
    avatar_url = JsonAttribute('')
    password_hash = JsonAttribute('')
    feed_urls = JsonAttribute('') # for now just semi-colon seperated string

    def set_password(self,p):
        """ sets users password hash based on passed string """
        self.password_hash = self.create_password_hash(p)

    password = property(lambda a: a.password_hash,
                        set_password)

    @classmethod
    def create_password_hash(cls,p):
        """ returns back hashed version of password """
        return sha1(p).hexdigest()

    def get_author(self):
        """ returns the author node for this user """
        # the author node for us will be the first author
        # node relative we have.
        # TODO: don't loop
        author_node = None
        for node in self.relatives:
            if isinstance(node,m.Author):
                author_node = node
                break

        # if we didn't find one create one
        if not author_node:
            author_node = m.Author(user_id=self.id)
            author_node.relatives.append(self)
            self.relatives.append(author_node)

        return author_node

    def __repr__(self):
        if self.handle:
            return self.handle
        if self.id:
            return '<User %s>' % self.id
        return '<User>'

class Author(JsonNode):
    """ User who author'd a node """
    user_id = JsonAttribute('')

    # over ride this to return the user
    # data along w/ our other data
    @staticmethod
    def _json_obj(node):
        if node.data:
            o = loads(node.data)
        else:
            o = {}

        # update with the user's data
        if node.user_id:
            user = m.User.get(node.user_id)
            if user:
                o.update(user.json_obj())

        o['id'] = node.id
        o['type'] = node.__class__.__name__
        return o

    def get_user(self):
        return [u for u in self.relatives if isinstance(u,m.User)][0]

class SexyLady(JsonNode):
    """ image(s) of sexy ladies """

    img_url = JsonAttribute('')
    source_href = JsonAttribute('')

    def save_down(self):
        ext = self.img_url.split('.')[-1]
        name = self.img_url.split('.')[-2].split('/')[-1]
        name = name.replace(os.sep,'')
        path = os.path.join(self.save_base,
                            self.__class__.__name__,
                            '%s_(%s).%s'%(name,self.id,ext))
        print 'saving: %s' % path
        with open(path,'w') as fh:
            fh.write(urlopen(self.img_url).read())
        return path

class SexyLadyFeed(JsonNode):
    url = JsonAttribute('')


