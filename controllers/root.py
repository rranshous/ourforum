import cherrypy
from helpers import render, redirect
from json import dumps
from lib.base import *
from nodes import Node
from auth import public, logout_user, login_user

class Root(BaseController):
    """ sits @ The root of the app """

    node = Node()

    @cherrypy.expose
    def default(self,*args,**kwargs):
        return render('/node.html');


    @cherrypy.expose
    @public
    def login(self,username=None,password=None,action=None,endpoint=None,
                   new_user=None):
        """ prompts the user to login, creates the user if it doesn't exist """


        # see if they are trying to login / create user
        if action or username or password:

            # if they didn't provide both username and password bounch them
            if not password or not username:
                error(403)
                add_flash('error','Your missing something!')


            # if they gave us a username and a password then they are
            # trying to login
            if not login_user(username,password):
                # fail !
                error(403)
                add_flash('error','Your login has failed!')

            else:

                # yay, success. push them to their next point
                if endpoint:
                    redirect(endpoint)

                # or home
                else:
                    redirect('/')


        return render('/login_front.html',username=username)

    @cherrypy.expose
    @public
    def logout(self):
        """ clear the sesion to logout the user """
        logout_user()
        redirect('/login')
