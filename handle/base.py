# -*- coding: utf-8 -*-

import json
import tornado.web
import sqlalchemy.orm.exc

from mako import exceptions

from model import Session



def authenticated(f):
    decorated = tornado.web.authenticated(f)
    decorated.authenticated = True;
    return decorated



def newline(text):
    return text.replace("\n", "<br />")



class BaseHandler(tornado.web.RequestHandler):

    def _execute(self, transforms, *args, **kwargs):
        method = self.get_argument("_method", None)
        if method and self.request.method.lower() == "post":
            self.request.method = method.upper()
        tornado.web.RequestHandler._execute(self, transforms, *args, **kwargs)

    @property
    def orm(self):
        return self.application.orm

    def content_type(self, name):
        if "Content-Type" in self.request.headers:
            return self.request.headers["Content-Type"].lower() == name.lower()
        return False

    def accept_type(self, name):
        if "Accept" in self.request.headers:
            return name.lower() in self.request.headers["Accept"].lower()
        return False

    def is_local(self):
        if "X-Forwarded-For" in self.request.headers:
            return False
        return self.request.remote_ip == "127.0.0.1"

    def get_remote_ip(self):
        if "X-Forwarded-For" in self.request.headers:
            return self.request.headers["X-Forwarded-For"]
        return self.request.remote_ip

    def get_accept_language(self):
        if "Accept-Language" in self.request.headers:
            return self.request.headers["Accept-Language"]
        return u""

    def get_user_agent(self):
        return self.request.headers["User-Agent"]

    def start_session(self, value):
        self.set_secure_cookie(self.application.session_cookie_name, value);
        # Sets a cookie value to the base64 plaintext session_id, 
        #   but is protected by tornado's _xsrf cookie.
        # Retrieved by BaseHandler.get_current_user()

    def end_session(self):
        self.clear_cookie(self.application.session_cookie_name)

    def render(self, template_name, **kwargs):
        template = self.application.lookup.get_template(template_name)
        kwargs["newline"] = newline
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
            session = self.orm.query(Session).\
                filter_by(session_id=session_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            self.end_session()
            return None
        if session.d_time is not None:
            self.end_session()
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
        self.render('error.html',
                    current_user=self.current_user, uri=self.request.uri,
                    status_code=self.status_code, message=message,
                    )

    _ARG_DEFAULT_MANGO = []
    def get_argument_float(self, name, default=_ARG_DEFAULT_MANGO, strip=True):
        value = self.get_argument(name, default, strip)
        if value == default:
            if default is self._ARG_DEFAULT_MANGO:
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return value

        try:
            return float(value)
        except ValueError as e:
            raise tornado.web.HTTPError(
                400,
                "Cannot convert argument %s to a floating point number." % name
                )

    def get_json_data(self):
        if hasattr(self, "json_data") and self.json_data:
            return
        try:
            self.json_data = json.loads(self.request.body)
        except ValueError as e:
            raise tornado.web.HTTPError(400, "Could not decode JSON data.")

    def get_json_argument(self, name, default=_ARG_DEFAULT_MANGO):
        self.get_json_data()

        if not name in self.json_data:
            if default is self._ARG_DEFAULT_MANGO:
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return default

        return self.json_data[name]

    def get_json_argument_float(self, name, default=_ARG_DEFAULT_MANGO):
        value = self.get_json_argument(name, default)
        if value == default:
            if default is self._ARG_DEFAULT_MANGO:
                raise tornado.web.HTTPError(400, "Missing argument %s" % name)
            return value

        try:
            return float(value)
        except ValueError as e:
            raise tornado.web.HTTPError(
                400,
                "Cannot convert argument %s to a floating point number." % name
                )

    def write_json(self, obj):
        self.write(json.dumps(obj, indent=2))

        


