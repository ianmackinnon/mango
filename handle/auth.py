# -*- coding: utf-8 -*-

import tornado.auth

from base import BaseHandler, authenticated

from model import User, Auth, Session


class AuthLoginHandler(BaseHandler):
    def get(self):
        self.render(
            'login.html',
            user=self.current_user,
            uri=self.request.uri,
            next=self.get_argument("next", "/")
            )



class AuthLoginLocalHandler(BaseHandler):
    def get(self):
        if not self.is_local():
            raise tornado.web.HTTPError(500, "Auth failed")

        user = self.orm.query(User).filter_by(user_id=-1).one()
        session = Session(
                user,
                self.get_remote_ip(),
                self.get_accept_language(),
                self.get_user_agent(),
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))
        self.redirect(self.get_argument("next", "/"))



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

        if not auth_user:
            raise tornado.web.HTTPError(500, "Google auth failed")

        auth_name = auth_user["email"]

        user = User.get_from_auth(self.orm, self.openid_url, auth_name)

        if not user:
            raise tornado.web.HTTPError(
                404, "%s %s: No account found" % (self.openid_url, auth_name)
                )

        session = Session(
                user,
                self.get_remote_ip(),
                self.get_accept_language(),
                self.get_user_agent(),
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


