import cherrypy
from helpers import render, redirect
from json import dumps
from lib.base import *
from nodes import Node

class Root(BaseController):
    """ sits @ The root of the app """

    nodes = Node()

    @cherrypy.expose
    def index(self):
        return render('/node.html');

