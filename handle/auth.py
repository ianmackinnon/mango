
import re
import json

import requests

import tornado.auth
from tornado.web import HTTPError
from sqlalchemy.orm.exc import NoResultFound

from model import User, Auth, Session

from handle.base import BaseHandler, authenticated



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

    @staticmethod
    def _check_locked(user):
        if user and user.locked:
            raise HTTPError(400, "Account locked.")

    def _check_registering(self, _user):
        register = self.app_get_cookie("register") or \
            bool(self.get_argument_bool("register", None))

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
        return session



class AuthLoginLocalHandler(LoginHandler):
    def _get_user(self):
        user_id = self.get_argument_int("user", -1)
        if user_id == 0:
            # Create new user
            return None
        try:
            return self.orm.query(User).filter_by(user_id=user_id).one()
        except NoResultFound:
            raise HTTPError(401, "Authorization Refused")

    def _create_user(self):
        user_id = self.get_argument_int("user", -1)
        assert user_id == 0
        user_name = "NEW USER"
        user = User(None, user_name, moderator=False)
        self.orm.add(user)
        self.orm.commit()
        user.name = "Local %d" % user.user_id
        self.orm.commit()
        self.next_ = "/user/%d" % user.user_id
        return user

    def get(self):
        if not self.application.local_auth:
            print("Local authentication is not enabled.")
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

        self._create_session(user)
        return self.redirect_next()



class AuthLoginGoogleHandler(LoginHandler, tornado.auth.GoogleOAuth2Mixin):
    # pylint: disable=no-value-for-parameter

    # Only used for our local database, not for actual auth
    openid_url = "https://www.google.com/accounts/o8/id"

    def _create_user(self, auth_user, auth_name):
        auth = Auth(self.openid_url, auth_name)
        user_name = str(auth_user["name"])
        user = User(auth, user_name, moderator=False)
        self.orm.add(user)
        self.orm.commit()
        self.next_ = "/user/%d" % user.user_id
        return user

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        redirect_path = self.url_rewrite("/auth/login/google")
        login_url = "%s://%s%s" % (
            self.request.protocol, self.request.host, redirect_path)

        if not self.get_argument('code', False):
            # Step 1. Send request to Google

            self._batch_tasks()

            if self.next_:
                self.app_set_cookie("next", self.next_)

            register = self.get_argument_bool("register", None)
            if register is not None:
                self.app_set_cookie("register", register)

            yield self.authorize_redirect(
                redirect_uri=login_url,
                client_id=self.settings['google_oauth']['key'],
                scope=['profile', 'email'],
                response_type='code',
                extra_params={'approval_prompt': 'auto',},
            )
        else:
            # Step 2. Recieving response from Google

            access_data = yield self.get_authenticated_user(
                redirect_uri=login_url,
                code=self.get_argument('code'))

            access_token = str(access_data['access_token'])
            uri = (
                "https://www.googleapis.com/oauth2/v1/userinfo?access_token=" +
                access_token
            )
            response = requests.get(uri)
            if response.status_code != 200:
                print(("Google auth status code: %s" % response.status_code))
                raise tornado.web.HTTPError(500, 'Server error')

            auth_user = json.loads(response.text)

            register = self.app_get_cookie("register")
            self.next_ = self.app_get_cookie("next")

            self.app_clear_cookie("register")
            self.app_clear_cookie("next")

            if not auth_user:
                raise HTTPError(500, "Google authentication failed")

            auth_name = auth_user["email"]
            user = User.get_from_auth(self.orm, self.openid_url, auth_name)

            if not user:
                if self._check_registering(user):
                    return
                user = self._create_user(auth_user, auth_name)

            self._check_locked(user)

            self._create_session(user)

            self.redirect_next()



class AuthVisitHandler(LoginHandler):
    def _create_user(self):
        user_name = "NEW USER"
        user = User(None, user_name, moderator=False)
        self.orm.add(user)
        self.orm.commit()
        user.name = "Anonymous %d" % user.user_id
        self.orm.commit()
        self.next_ = "/user/%d" % user.user_id
        return user

    def get(self):
        self._accept_authenticated()

        self._batch_tasks()

        user = self._create_user()

        self._create_session(user)
        return self.redirect_next()



class AuthLogoutHandler(BaseHandler):
    def path_is_authenticated(self, path):
        if path.startswith(self.url_root):
            path = "/" + path[len(self.url_root):]
        for row in self.application.handlers:
            key, value = row[:2]
            if re.match(key, path) and hasattr(value, "get"):
                if (
                        hasattr(value.get, "authenticated") and \
                        value.get.authenticated is True
                ):
                    return True
        return False

    @authenticated
    def get(self):
        session = self.get_session()
        if session:
            session.close_commit()
        self.end_session()
        self.clear_cookie("_xsrf")
        if self.next_:
            if (not self.moderator) or self.path_is_authenticated(self.next_):
                self.next_ = self.url_root
        return self.redirect_next()



def delete_inactive_users(orm):
    away_time = 60 * 60 * 24 * 30  # 30 Days in seconds

    inner_sql = """select
    user_id,
    unix_timestamp() - max(session.a_time) as away
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

    session_sql = """delete
  from session
  where exists (
    select 1
      from (
        %s
      ) as q2
      where q2.user_id = session.user_id
    )
  ;""" % inner_sql
    user_sql = """delete
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
