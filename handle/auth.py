# -*- coding: utf-8 -*-

import re
from urllib import urlencode

import tornado.auth
from tornado.web import HTTPError
from sqlalchemy.orm.exc import NoResultFound

from base import BaseHandler, authenticated
from model import User, Auth, Session


class AuthRegisterHandler(BaseHandler):
    def get(self):
        self.next = self.url_rewrite("/user/self", parameters={})
        self.render(
            'register.html',
            next=self.next,
            )



class AuthLoginLocalHandler(BaseHandler):
    def get(self):
        if not self.is_local():
            raise tornado.web.HTTPError(404, "Not found")
        user_id = self.get_argument_int("user", -1)
        try:
            user = self.orm.query(User).filter_by(user_id=user_id).one()
        except NoResultFound:
            raise tornado.web.HTTPError(404, "Not found")
        session = Session(
                user,
                self.get_remote_ip(),
                self.get_accept_language(),
                self.get_user_agent(),
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))
        self.orm.commit()
        return self.redirect_next()



class AuthLoginGoogleHandler(BaseHandler, tornado.auth.GoogleMixin):

    openid_url = u"https://www.google.com/accounts/o8/id"
    
    @tornado.web.asynchronous
    def get(self):
        if self.current_user:
            return self.redirect_next()

        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        login_args = {
            "next": self.next or self.application.url_root,
            }
        login_url = self.get_login_url() + "?" + urlencode(login_args)
        self.authenticate_redirect(login_url)
    
    def _on_auth(self, auth_user):
        """
        Called after we receive authorisation information from Google.
        auth_user dict is either empty or contains 'locale', 'first_name', 'last_name', 'name' and 'email'.
        """

        if not auth_user:
            raise HTTPError(500, "Google authentication failed")

        auth_name = auth_user["email"]

        user = User.get_from_auth(self.orm, self.openid_url, auth_name)

        if not user:
            auth = Auth(self.openid_url, auth_name)
            user_name = unicode(auth_user["name"])
            user = User(auth, user_name, moderator=False)
            self.orm.add(user)
            self.orm.commit()
            self.next = "/user/%d" % user.user_id

        if user and user.locked:
            raise HTTPError(400, "Account locked.")

        session = Session(
                user,
                self.get_remote_ip(),
                self.get_accept_language(),
                self.get_user_agent(),
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))
        self.orm.commit()

        return self.redirect_next()



class AuthVisitHandler(BaseHandler):
    def get(self):
        if self.current_user:
            return self.redirect_next()
        
        user_name = "NEW USER"
        user = User(None, user_name, moderator=False)
        self.orm.add(user)
        self.orm.commit()
        user.name = "Anonymous %d" % user.user_id
        self.orm.commit()
        self.next = "/user/%d" % user.user_id

        session = Session(
                user,
                self.get_remote_ip(),
                self.get_accept_language(),
                self.get_user_agent(),
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))
        self.orm.commit()

        return self.redirect_next()




class AuthLogoutHandler(BaseHandler):
    def path_is_authenticated(self, path):
        if path.startswith(self.url_root):
            path = "/" + path[len(self.url_root):]
        for row in self.application.handlers:
            key, value = row[:2]
            if re.match(key, path) and hasattr(value, "get"):
                if hasattr(value.get, "authenticated") and \
                        value.get.authenticated == True:
                    return True
        return False

    def get(self):
        session = self.get_session()
        if session:
            session.close_commit()
        self.end_session()
        self.clear_cookie("_xsrf")
        if self.next and self.path_is_authenticated(self.next):
            self.next = self.url_root
        return self.redirect_next()



