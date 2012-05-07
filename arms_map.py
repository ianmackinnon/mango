#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import errno
import logging

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

import sqlalchemy.orm.exc
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine


from model import Auth, User, Session, Organisation



define("port", default=8802, help="run on the given port", type=int)



class Application(tornado.web.Application):

    session_cookie_name = "arms-data"

    def load_cookie_secret(self):
        try:
            self.cookie_secret = open(".xsrf", "r").read().strip()
        except IOError as e:
            sys.stderr.write("Could not open XSRF key. Run 'make' to generate one.\n")
            sys.exit(1)

    def path_is_authenticated(self, path):
        for key, value in self.handler_list:
            if re.match(key, path) and hasattr(value, "get"):
                if hasattr(value.get, "authenticated") and value.get.authenticated == True:
                    return True
        return False
                
        
    def __init__(self):
        self.load_cookie_secret()

        settings = dict(
            xsrf_cookies=True,
            cookie_secret=self.cookie_secret,
            login_url="/auth/login",
            )

        re_id = "([1-9][0-9]*)"

        self.handler_list = [
            (r"/", HomeHandler),

            (r"/user", UserListHandler),
            (r"/user/%s" % re_id , UserHandler),

            (r"/organisation", OrganisationListHandler),
            (r"/organisation/%s" % re_id, OrganisationHandler),

            (r"/auth/login", AuthLoginHandler),
            (r"/auth/login/google", AuthLoginGoogleHandler),
            (r"/auth/logout", AuthLogoutHandler),
            ]

        
        connection_url = 'sqlite:///arms-map.db'
    
        engine = create_engine(connection_url)

        self.orm = scoped_session(sessionmaker(bind=engine))

        self.lookup = TemplateLookup(directories=['template'],
                                     input_encoding='utf-8',
                                     output_encoding='utf-8',
                                     default_filters=["unicode", "h"],
                                     )

        log_location = "log/arms_map.py.log"
        log_max_bytes = 1048576

        try:
            os.mkdir(os.path.dirname(log_location))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e
            

        logger = logging.getLogger()
        handler = logging.handlers.RotatingFileHandler(log_location, maxBytes=log_max_bytes)
        logging.getLogger().addHandler(handler)
        
        tornado.web.Application.__init__(self, self.handler_list, **settings)

    
        
class BaseHandler(tornado.web.RequestHandler):

    def _execute(self, transforms, *args, **kwargs):
        method = self.get_argument("_method", None)
        if method and self.request.method.lower() == "post":
            self.request.method = method.upper()
        tornado.web.RequestHandler._execute(self, transforms, *args, **kwargs)

    @property
    def orm(self):
        return self.application.orm

    def start_session(self, value):
        self.set_secure_cookie(self.application.session_cookie_name, value);
        # Sets a cookie value to the base64 plaintext session_id, 
        #   but is protected by tornado's _xsrf cookie.
        # Retrieved by BaseHandler.get_current_user()

    def end_session(self):
        self.clear_cookie(self.application.session_cookie_name)

    def render(self, template_name, **kwargs):
        template = self.application.lookup.get_template(template_name)
        try:
            self.write(template.render(**kwargs))
        except:
            self.write(exceptions.html_error_template().render())
        if self.orm.new or self.orm.dirty or self.orm.deleted:
            print self.orm.new or self.orm.dirty or self.orm.deleted
            self.orm.rollback()

    def get_session(self):
        session_id = self.get_secure_cookie(self.application.session_cookie_name)
        try:
            session = self.orm.query(Session).filter_by(session_id=session_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return None
        if session.d_time is not None:
            return None
        session.touch_commit()
        return session

    # required by tornado auth
    def get_current_user(self):
        session = self.get_session()
        if session:
            return session.user
        return None

    def error(self, status_code, message):
        self.status_code = status_code
        self.render('error.html', current_user=self.current_user, uri=self.request.uri, status_code=self.status_code, message=message)



def authenticated(f):
    decorated = tornado.web.authenticated(f)
    decorated.authenticated = True;
    return decorated



class HomeHandler(BaseHandler):
    def get(self):
        self.render('home.html', current_user=self.current_user, uri=self.request.uri)



class OrganisationListHandler(BaseHandler):
    def get(self):
        organisation_list = self.orm.query(Organisation).all()
        self.render('organisation_list.html', current_user=self.current_user, uri=self.request.uri, organisation_list=organisation_list, xsrf=self.xsrf_token)

    @authenticated
    def post(self):
        name = self.get_argument("name")
        organisation = Organisation(name)
        self.orm.add(organisation)
        self.orm.commit()
        self.redirect(organisation.url)

class OrganisationHandler(BaseHandler):
    def get(self, organisation_id_string):
        organisation_id = int(organisation_id_string)
        try:
            organisation = self.orm.query(Organisation).filter_by(organisation_id=organisation_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such organisation" % organisation_id)
        self.render('organisation.html', current_user=self.current_user, uri=self.request.uri, xsrf=self.xsrf_token, organisation=organisation)

    @authenticated
    def delete(self, organisation_id_string):
        organisation_id = int(organisation_id_string)
        try:
            organisation = self.orm.query(Organisation).filter_by(organisation_id=organisation_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such organisation" % organisation_id)
        self.orm.delete(organisation)
        self.redirect("/organisation")
        
    @authenticated
    def put(self, organisation_id_string):
        organisation_id = int(organisation_id_string)
        try:
            organisation = self.orm.query(Organisation).filter_by(organisation_id=organisation_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such organisation" % organisation_id)
        name = self.get_argument("name")
        organisation.name = name
        self.orm.commit()
        self.redirect(organisation.url)
        


class UserListHandler(BaseHandler):
    @authenticated
    def get(self):
        user_list = self.orm.query(User).all()
        self.render('user_list.html', current_user=self.current_user, uri=self.request.uri, user_list=user_list)

class UserHandler(BaseHandler):
    @authenticated
    def get(self, user_id_string):
        user_id = int(user_id_string)
        try:
            user = self.orm.query(User).filter_by(user_id=user_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such user" % user_id)
        self.render('user.html', current_user=self.current_user, uri=self.request.uri, xsrf=self.xsrf_token, user=user)



# Authentication pages



class AuthLoginHandler(BaseHandler):
    def get(self):
        self.render('login.html', user=self.current_user, uri=self.request.uri, next=self.get_argument("next", "/"))



class AuthLoginGoogleHandler(BaseHandler, tornado.auth.GoogleMixin):

    openid_url = u"https://www.google.com/accounts/o8/id"
    
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()
    
    def _on_auth(self, auth_user):
        """
        Called after we receive authorisation information from Google.
        auth_user dict is either empty or contains 'locale', 'first_name', 'last_name', 'name' and 'email'.
        """

        print "on auth"

        if not auth_user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        auth_name = auth_user["email"]

        print auth_name

        user = User.get_from_auth(self.orm, self.openid_url, auth_name)

        print user

        if not user:
            return self.error(404, "%s %s: No account found" % (self.openid_url, auth_name))

        session = Session(
                user,
                self.request.remote_ip,
                self.request.headers["Accept-Language"],
                self.request.headers["User-Agent"]
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))

        self.redirect(self.get_argument("next", "/"))



class AuthLogoutHandler(BaseHandler):
    def get(self):
        session = self.get_session()
        if session:
            session.close_commit()
        self.end_session()
        self.clear_cookie("_xsrf")
        next_path = self.get_argument("next", "/")
        if self.application.path_is_authenticated(next_path):
            next_path = "/"
        self.redirect(next_path)



def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
