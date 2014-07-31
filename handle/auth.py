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
        self.next_ = self.url_rewrite("/user/self", parameters={})
        self.render(
            'register.html',
            next_=self.next_,
            )


class LoginHandler(BaseHandler):
    def _accept_authenticated(self):
        if self.current_user:
            return self.redirect_next()

    def _batch_tasks(self):
        delete_inactive_users(self.orm)

    def _check_locked(self, user):
        if user and user.locked:
            raise HTTPError(400, "Account locked.")

    def _check_registering(self, user):
        register = self.get_argument_bool("register", None)

        if not register:
            self.redirect(self.url_rewrite("/auth/register", next_=self.next_))
            return True

    def _create_session(self, user):
        session = Session(
                user,
                self.request.remote_ip,
                self.get_accept_language(),
                self.get_user_agent(),
                )
        self.orm.add(session)
        self.orm.flush()
        self.start_session(str(session.session_id))
        self.orm.commit()



class AuthLoginLocalHandler(LoginHandler):
    def _get_user(self):
        user_id = self.get_argument_int("user", -1)
        if user_id == 0:
            # Create new user
            return None
        try:
            return self.orm.query(User).filter_by(user_id=user_id).one()
        except NoResultFound as e:
            raise HTTPError(401, "Authorization Refused")

    def _create_user(self):
        user_id = self.get_argument_int("user", -1)
        assert user_id == 0
        user_name = u"NEW USER"
        user = User(None, user_name, moderator=False)
        self.orm.add(user)
        self.orm.commit()
        user.name = u"Local %d" % user.user_id
        self.orm.commit()
        self.next_ = "/user/%d" % user.user_id
        return user
    
    def get(self):
        if not self.application.local_auth:
            print u"Local authentication is not enabled."
            raise HTTPError(404, "Not found")
        if not self.is_local():
            raise HTTPError(404, "Not found")

        self._accept_authenticated()

        self._batch_tasks()

        user = self._get_user()
        self._check_locked(user)
        
        if not user:
            if self._check_registering(user):
                return
            user = self._create_user()

        session = self._create_session(user)
        return self.redirect_next()



class AuthLoginGoogleHandler(LoginHandler, tornado.auth.GoogleMixin):

    openid_url = u"https://www.google.com/accounts/o8/id"

    def _get_user(self):
        if not self.auth_user:
            raise HTTPError(500, "Google authentication failed")

        self.auth_name = self.auth_user["email"]
        return User.get_from_auth(self.orm, self.openid_url, self.auth_name)

    def _create_user(self):
        auth = Auth(self.openid_url, self.auth_name)
        user_name = unicode(self.auth_user["name"])
        user = User(auth, user_name, moderator=False)
        self.orm.add(user)
        self.orm.commit()
        self.next_ = "/user/%d" % user.user_id
        return user
    
    @tornado.web.asynchronous
    def get(self):

        self._accept_authenticated()

        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return

        self._batch_tasks()

        register = self.get_argument_bool("register", None)
        login_args = {
            "next": self.next_ or self.application.url_root,
            }
        if register is not None:
            login_args["register"] = int(register)
        login_url = self.get_login_url() + "?" + urlencode(login_args)
        self.authenticate_redirect(login_url)
    
    def _on_auth(self, auth_user):
        """
        Called after we receive authorisation information from Google.
        auth_user dict is either empty or contains 'locale', 'first_name', 'last_name', 'name' and 'email'.
        """

        self.auth_user = auth_user

        user = self._get_user()
        self._check_locked(user)

        if not user:
            if self._check_registering(user):
                return
            user = self._create_user()

        session = self._create_session(user)
        return self.redirect_next()



class AuthVisitHandler(LoginHandler):
    def _get_user(self):
        return None

    def _check_locked(self, user):
        pass

    def _check_registering(self, user):
        pass

    def _create_user(self):
        user_name = u"NEW USER"
        user = User(None, user_name, moderator=False)
        self.orm.add(user)
        self.orm.commit()
        user.name = u"Anonymous %d" % user.user_id
        self.orm.commit()
        self.next_ = "/user/%d" % user.user_id
        return user
    
    def get(self):
        self._accept_authenticated()

        self._batch_tasks()

        user = self._get_user()
        self._check_locked(user)
        
        if not user:
            if self._check_registering(user):
                return
            user = self._create_user()

        session = self._create_session(user)
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
        if self.next_ and self.path_is_authenticated(self.next_):
            self.next_ = self.url_root
        return self.redirect_next()



def delete_inactive_users(orm):
    away_time = 60 * 60 * 24 * 30  # 30 Days in seconds
    away_time = 10

    inner_sql = u"""select user_id, unix_timestamp() - max(session.a_time) as away
  from user
  left outer join session using (user_id)
  where auth_id is null
    and not exists (
      select moderation_user_id
        from (
          select distinct(moderation_user_id)
            from org_v
          union select distinct(moderation_user_id)
            from event_v
          union select distinct(moderation_user_id)
            from address_v
          union select distinct(moderation_user_id)
            from contact_v
          ) as q1
        where q1.moderation_user_id = user_id
    )
  group by user_id
  having away is null or away > %d""" % away_time

    session_sql = u"""delete
  from session
  where exists (
    select 1
      from (
        %s
      ) as q2
      where q2.user_id = session.user_id
    )
  ;""" % inner_sql
    user_sql = u"""delete
  from user
  where exists (
    select 1
      from (
        %s
      ) as q2
      where q2.user_id = user.user_id
    )
  ;""" % inner_sql
    
    engine = orm.connection().engine

    engine.execute("Begin")
    engine.execute(session_sql)
    engine.execute(user_sql)
    engine.execute("Commit")



