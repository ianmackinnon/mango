# -*- coding: utf-8 -*-

import tornado.auth

from base import BaseHandler, authenticated

from model import User, Auth, Session


class AuthLoginHandler(BaseHandler):
    def get(self):
        self.render(
            'login.html',
            next=self.next or self.application.url_root,
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
        self.redirect(self.next or self.application.url_root)



class AuthLoginGoogleHandler(BaseHandler, tornado.auth.GoogleMixin):

    openid_url = u"https://www.google.com/accounts/o8/id"
    
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect(self.get_login_url())
    
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
            self.error(404, "No account found for %s" % auth_user["email"])
            return

        session = Session(
                user,
                self.get_remote_ip(),
                self.get_accept_language(),
                self.get_user_agent(),
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))

        self.redirect(self.next or self.application.url_root)



class AuthLogoutHandler(BaseHandler):
    def get(self):
        session = self.get_session()
        if session:
            session.close_commit()
        self.end_session()
        self.clear_cookie("_xsrf")
        if self.next and self.application.path_is_authenticated(self.next):
            self.next = self.application.url_root
        self.redirect(self.next or self.application.url_root)



