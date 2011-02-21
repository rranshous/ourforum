from elixir import *
import datetime
import cherrypy
from hashlib import sha1
import models as m
import os
import random
from json import dumps, loads

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
    def __setitem__(self,k,v):
        super(SetHookDict,self).__setitem__(k,v)
        if hasattr(self,'callback'):
            self.callback(self)

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

    @classmethod
    def get_json_obj(cls,node_id):
        """ returns either the json obj for the node
            or None """
        node = cls.get(node_id)
        if node:
            return loads(node.data)
        return None

    def json_obj(self):
        return loads(self.data or {})

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

    def __init__(self,*args,**kwargs):
        """
        setup attributes in the json data for our
        JsonAttribute's as well as the kwargs
        """

        # call our super
        super(JsonNode,self).__init__(*args,**kwargs)

        # update our data dict w/ the base
        # attributes
        for k,v in vars(self).iteritems():
            if isinstance(v,JsonAttribute):
                data[k] = v.default

        # update our data dict from the kwargs
        for k,v in kwargs.iteritems():
            data[k] = v

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

class FeedEntry(JsonNode):
    """
    a node based off an RSS feed entry
    """

    title = JsonAttribute('')
    body = JsonAttribute('')
    timestamp = JsonAttribute('')

class Comment(JsonNode):
    """
    a comment probably entered through the site
    """

    title = JsonAttribute('')
    comment = JsonAttribute('')

class User(JsonNode):
    """
    The user node will hold info about the users.
    """

    handle = JsonAttribute()
    avatar_url = JsonAttribute()
    password_hash = JsonAttribute()

    def set_password(self,p):
        """ sets users password hash based on passed string """
        self.password_hash = self.create_password_hash(p)

    password = property(lambda a: a.password_hash,
                        set_password)

    @classmethod
    def create_password_hash(cls,p):
        """ returns back hashed version of password """
        return sha1(p).hexdigest()

