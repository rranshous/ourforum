import cherrypy
from helpers import render, redirect
from json import dumps
from lib.base import *
from nodes import Node

class Root(BaseController):
    """ sits @ The root of the app """

    node = Node()

    @cherrypy.expose
    def default(self,*args,**kwargs):
        return render('/node.html');

