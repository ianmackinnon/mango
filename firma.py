#!/usr/bin/env python3

import os
import re
import sys
import time
import json
import errno
import bisect
import base64
import logging
import datetime
import functools
import urllib.parse
import configparser

from dateutil.relativedelta import relativedelta

from onetimepass import valid_totp

import tornado.web
import tornado.auth
import tornado.httpserver
import tornado.options
import tornado.ioloop
from tornado import escape
from tornado.log import app_log

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm.exc import NoResultFound



DEFAULTS = {
    "port": 8000,
    "host": "localhost",
}

ARG_DEFAULT = []



def conf_get(ini_path, section, key, default=ARG_DEFAULT):
    # pylint: disable=dangerous-default-value
    # Using `[]` as default value in `get`

    config = configparser.ConfigParser()
    config.read(ini_path)

    try:
        value = config.get(section, key)
    except configparser.NoOptionError:
        if default == ARG_DEFAULT:
            raise
        return default

    return value



class Settings(dict):
    def __getattr__(self, key):
        value = self.get(key)
        if isinstance(value, dict) and not isinstance(value, Settings):
            self[key] = Settings(value)
            value = self.get(key)
        return value


    def __setattr__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, Settings):
            value = Settings(value)
        self[key] = value

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, Settings):
            value = Settings(value)
        super(Settings, self).__setitem__(key, value)

    def update(self, *args):
        for iter_ in args:
            for key in iter_:
                if (
                        key in self and
                        isinstance(self[key], dict) and
                        isinstance(iter_[key], dict)
                ):
                    self[key].update(iter_[key])
                else:
                    self[key] = iter_[key]



class Application(tornado.web.Application):
    stats = None

    RESPONSE_LOG_DURATION = 5 * 60  # Seconds
    SESSION_COOKIE_PATH = None

    # Stats

    def init_stats(self):
        self.stats = []

    def add_stat(self, key, value):
        self.stats.append((key, value))

    def write_stats(self):
        self.add_stat(
            "Started",
            datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        sys.stdout.write("%s is running.\n" % self.title)
        for key, value in self.stats:
            sys.stdout.write("  %-20s %s\n" % (key + ":", value))
        sys.stdout.flush()


    # Cookies

    @staticmethod
    def load_cookie_secret():
        try:
            return open(".xsrf", "r").read().strip()
        except IOError:
            sys.stderr.write(
                "Could not open XSRF key. Run 'make .xsrf' to generate one.\n")
            sys.exit(1)

    def init_cookies(self, prefix):
        cookie_secret = self.load_cookie_secret()
        self.settings.update({
            "xsrf_cookies": True,
            "cookie_secret": cookie_secret,
        })
        self.settings.app.cookie_prefix = prefix
        self.add_stat("Cookie prefix", prefix)


    # Response Log

    @tornado.gen.coroutine
    def trim_response_log(self):
        start = time.time() - self.RESPONSE_LOG_DURATION
        row = [start, None, None]
        index = bisect.bisect(self.settings.app.response_log, row)
        self.settings.app.response_log = self.settings.app.response_log[index:]

    def init_response_log(self, app):
        app["response_log"] = []
        tornado.ioloop.PeriodicCallback(
            self.trim_response_log,
            self.RESPONSE_LOG_DURATION * 1000
        ).start()


    # Sibling Applications

    def init_sibling(self, name, conf_path, parameter):
        if not self.settings.app.siblings:
            self.settings.app.siblings = {}

        self.settings.app.siblings[name] = {}
        sibling = self.settings.app.siblings[name]

        conf_url = conf_get(conf_path, 'app', parameter)
        sibling.url = conf_url or None

        self.add_stat(
            "URL %s" % name,
            sibling.url or "offline"
        )


    # URI Log

    def init_log(self, options, name, propagate=None, level=None):
        log = self.settings.app.log

        log[name] = {
            "log": logging.getLogger(
                name if name.startswith("tornado")
                else '%s.%s' % (self.name, name)
            )
        }

        if propagate is not None:
            log[name].log.propagate = propagate
        if level is not None:
            log[name].log.setLevel(level)
        if options.log:
            try:
                os.makedirs(options.log)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise e

            log[name].path = os.path.join(
                options.log,
                '%s.%s.log' % (self.name, name)
            )

            log[name].log.addHandler(
                logging.handlers.TimedRotatingFileHandler(
                    log[name].path,
                    when="midnight",
                    encoding="utf-8",
                    backupCount=7,
                    utc=True
                )
            )
        else:
            log[name].log.addHandler(logging.NullHandler())

    # Databases

    def mysql_attach_secondary(self, db_key, db_name, query_string):
        if self.settings.app.database is None:
            self.settings.app.database = {}
        db = self.settings.app.database

        db[db_key] = {}
        db[db_key]["database"] = db_name
        db[db_key]["connected"] = False
        db[db_key]["status"] = None

        try:
            self.orm.execute(query_string % db_name).scalar()
            self.mysql_db_success(db_key)
        except OperationalError as e:
            self.mysql_db_failure(db_key, e)

        self.add_stat(
            "MySQL %s" % db_key,
            "%s (%s)" % (db[db_key]["status"], db_name)
        )

    def mysql_db_success(self, db_key):
        db = self.settings.app.database
        db_name = db[db_key]["database"]
        if not db[db_key]["connected"]:
            app_log.info(
                "Successfully connected to MySQL %s DB '%s'.",
                db_key, db_name)
        db[db_key]["connected"] = True
        db[db_key]["status"] = "Connected"

    def mysql_db_failure(self, db_key, error):
        db = self.settings.app.database
        db_name = db[db_key]["database"]
        if db[db_key].connected:
            app_log.warning(
                "Lost connection to MySQL %s DB '%s'. %s",
                db_key, db_name, str(error))
        elif db[db_key].status is None:
            app_log.warning(
                "Failed to connect to MySQL %s DB '%s'. %s",
                db_key, db_name, str(error))

        db[db_key]["connected"] = False
        if "denied" in str(error):
            db[db_key]["status"] = "Access denied"
        else:
            db[db_key]["status"] = "Cannot connect"

    def mysql_db_name(self, db_key):
        return self.settings.app.database and \
            self.settings.app.database[db_key] and \
            self.settings.app.database[db_key].database


    # Initialisation


    def init_settings(self, options):
        self.settings.options = options
        self.settings.app = {}
        self.settings.app.log = {}

        self.add_stat("Address",
                      "http://localhost:%d" % self.settings.options.port)
        if self.settings.options.label:
            self.add_stat("Label", self.settings.options.label)

    def __init__(self, handlers, options, **settings):
        assert self.name
        assert self.title

        self.label = options.label

        self.init_stats()
        self.settings = Settings(settings or {})
        self.init_settings(options)

        self.init_log(options, "uri", propagate=False, level=logging.INFO)
        self.init_log(options, "tornado")

        if self.settings.options.status:
            handlers.insert(1, (r"/server-status", ServerStatusHandler))
            self.init_response_log(self.settings.app)

        _settings = self.settings
        # Resets `self.settings`:
        super(Application, self).__init__(handlers, **settings)
        self.settings = _settings
        self.write_stats()



class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.start = None
        self.url_root = self.request.headers.get("X-Forwarded-Root", "/")
        sys.stdout.flush()

    # Utilities

    @property
    def settings(self):
        return self.application.settings

    @property
    def url_root_dir(self):
        """
        Return the root path without a trailing slash.
        """
        if self.url_root == "/":
            return self.url_root
        return self.url_root.rstrip("/")


    # Lifecycle

    def prepare(self):
        self.start = time.time()

    def on_finish(self):
        if not hasattr(self, "start") or self.start is None:
            return
        now = time.time()
        duration = now - self.start
        self.settings.app.log.uri.log.info(
            "%s, %s, %s, %s, %0.3f",
            str(now),
            self.request.uri,
            self.request.remote_ip,
            repr(self.request.headers.get("User-Agent", "User-Agent")),
            duration
        )

        if self.settings.app.response_log is not None:
            response = [now, self._status_code, duration]
            self.settings.app.response_log.append(response)


    # Cookies

    def cookie_name(self, name):
        return "-".join([_f for _f in [
            self.settings.app.cookie_prefix, name] if _f])


    def app_set_cookie(self, key, value, **kwargs):
        """
        Uses app prefix and URL root for path.
        Stringify as JSON. Always set secure.
        """

        # Path cannot be `None`
        if "path" in kwargs and not kwargs["path"]:
            del kwargs["path"]

        kwargs = dict(list({
            "path": self.url_root_dir
        }.items()) + list((kwargs or {}).items()))

        key = self.cookie_name(key)
        value = json.dumps(value)

        self.set_secure_cookie(key, value, **kwargs)


    def app_get_cookie(self, key, secure=True):
        "Uses app prefix. Secure by default. Parse JSON."

        key = self.cookie_name(key)

        if secure:
            # Returns `bytes`
            value = self.get_secure_cookie(key)
            if value:
                value = value.decode()
        else:
            # Returns `str`
            value = self.get_cookie(key)

        return value and json.loads(value)


    def app_clear_cookie(self, key, **kwargs):
        """
        Uses app prefix and URL root for path.
        """

        kwargs = kwargs or {}
        kwargs.update({
            "path": self.url_root
        })

        self.clear_cookie(self.cookie_name(key), **kwargs)


    # Sessions

    """
    `Session` type should be a SQLAlchemy model like so:

    class Session(Base):
        ...

        session_id = Column(Integer, primary_key=True)
        delete_time = Column(Float)
        ip_address = Column(String, nullable=False)
        accept_language = Column(String, nullable=False)
        user_agent = Column(String, nullable=False)
        user = relationship(User, backref='session_list')

        def __init__(
            self, user,
            ip_address=None, accept_language=None, user_agent=None
        ):
        ...

    """  # pylint: disable=pointless-string-statement

    def get_accept_language(self):
        return self.request.headers.get("Accept-Language", "")

    def get_user_agent(self):
        return self.request.headers.get("User-Agent", "")

    def start_session(self, value):
        self.app_set_cookie(
            "session", value, path=self.application.SESSION_COOKIE_PATH)

    def end_session(self):
        self.app_clear_cookie(
            "session", path=self.application.SESSION_COOKIE_PATH)

    def create_session(self, user, Session):
        # pylint: disable=invalid-name
        # `Session` is a class.

        session = Session(
            user,
            self.request.remote_ip,
            self.get_accept_language(),
            self.get_user_agent(),
        )
        self.orm.add(session)
        self.orm.flush()

        self.orm.commit()

        self.start_session(str(session.session_id))

        return session

    def compare_session(self, session):
        """
        Returns falsy if equal, truthy if different.
        """
        return \
            session.ip_address not in (
                self.request.remote_ip,
                self.request.headers.get("X-Remote-Addr", None)
            ) or \
            session.accept_language != self.get_accept_language() or \
            session.user_agent != self.get_user_agent()

    def get_session(self, Session):
        # pylint: disable=invalid-name
        # `Session` is a class.

        session_id = self.app_get_cookie("session")

        try:
            session_id = int(session_id)
        except (ValueError, TypeError):
            return None

        try:
            session = self.orm.query(Session).\
                filter_by(session_id=session_id).one()
        except NoResultFound:
            self.end_session()
            return None

        if session.delete_time is not None:
            self.end_session()
            return None

        if self.compare_session(session):
            self.end_session()
            return None

        session.touch_commit()

        return session




    # Arguments

    def get_argument_int(self, name, default):
        """
        Returns a signed integer, or
        `default` if value cannot be converted.
        """
        value = self.get_argument(name, default)
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = default
        return value

    def get_argument_date(self, name, default, end=None):
        """
        Returns a date (year, month, day) based on a variable-length
        string. If `end` is falsy, returns the earliest possible date,
        ie. "2011" returns "1st of January 2011", otherwise, returns
        the day after the latest possible date, eg. "2012-08" returns
        "2012-09-01".
        """
        value = self.get_argument(name, default)
        if not value:
            return default

        match = re.compile("""^
        ([0-9]{4})
        (?:
        -([0-9]{2})
        (?:
        -([0-9]{2})
        )?
        )?""", re.U | re.X).match(value)

        if not match:
            return default

        match = [v and int(v) for v in match.groups()]

        delta = None

        if end:
            if match[1] is None:
                delta = relativedelta(years=1)
            elif match[2] is None:
                delta = relativedelta(months=1)
            else:
                delta = relativedelta(days=1)
        if match[1] is None:
            match[1] = 1
            match[2] = 1
        elif match[2] is None:
            match[2] = 1

        vdate = datetime.date(*match)

        if delta:
            vdate += delta

        return vdate

    def get_argument_int_set(self, name):
        """
        Returns a list of unique signed integers. They may
        be supplied as multiple and/or comma-separated parameters
        """

        values = set([])
        raw = self.get_arguments(name)
        for text in raw:
            for part in text.split(","):
                try:
                    id_ = int(part)
                except ValueError:
                    continue
                values.add(id_)
        return sorted(list(values))



class AuthGoogleOAuth2UserMixin(tornado.auth.GoogleOAuth2Mixin):
    @staticmethod
    def _on_user_data(future, response):
        """Callback function for the exchange to the user data."""
        if response.error:
            future.set_exception(tornado.auth.AuthError(
                "Google user data error: %s" % str(response)))
            return

        args = escape.json_decode(response.body)
        future.set_result(args)

    @tornado.auth._auth_return_future  # pylint: disable=protected-access
    def get_user_data(self, access_data, callback):
        http = self.get_auth_http_client()
        http.fetch(
            self._OAUTH_USERINFO_URL + "?" + urllib.parse.urlencode({
                "access_token": access_data["access_token"]
            }),
            functools.partial(self._on_user_data, callback),
        )



class UserMixin(object):
    """
    Client class should be a SQLAlchemy model with attributes
    `password_hash`.
    `onetime_secret`.
    """

    # pylint: disable=not-callable
    # `HASH_ALG` must be defined as a hashing function

    HASH_ALG = None
    SALT_LENGTH = None
    SECRET_LENGTH = 16

    def set_password_hash(self, plaintext):
        """
        `plaintext` is UTF-8 encoded
        """
        hasher = self.HASH_ALG()
        hex_length = hasher.digest_size * 2
        hasher.update(os.urandom(hex_length))
        salt = hasher.hexdigest()[:self.SALT_LENGTH]
        payload = (salt + plaintext).encode("utf-8")

        hasher = self.HASH_ALG()
        hash_ = self.HASH_ALG(payload).hexdigest()
        salted_hash = (salt + hash_)[:hex_length]
        self.password_hash = salted_hash

    def verify_password_hash(self, plaintext):
        """
        `plaintext` is UTF-8 encoded
        Returns `True` if plaintext matches hash.
        """
        if not self.password_hash:
            return None

        salt = self.password_hash[:self.SALT_LENGTH]
        payload = (salt + plaintext).encode("utf-8")

        hasher = self.HASH_ALG()
        hex_length = hasher.digest_size * 2
        hash_ = self.HASH_ALG(payload).hexdigest()
        salted_hash = (salt + hash_)[:hex_length]
        return self.password_hash == salted_hash

    def set_onetime_secret(self):
        secret = base64.b32encode(os.urandom(10))
        self.onetime_secret = secret
        return secret

    def verify_onetimepass(self, token):
        if not self.password_hash:
            return None

        return valid_totp(token, self.onetime_secret)





class ServerStatusHandler(tornado.web.RequestHandler):
    @staticmethod
    def median_sorted(data):
        if not data:
            return
        if len(data) == 1:
            return data[0]
        half = int(len(data) / 2)
        if len(data) % 2:
            return (data[half - 1] +
                    data[half]) / 2
        else:
            return data[half]

    @staticmethod
    def quartiles(data):
        """
        Accepts an unsorted list of floats.
        """
        if not data:
            return
        sample = sorted(data)

        if len(data) == 1:
            median = data[0]
            q1 = data[0]
            q3 = data[0]
        else:
            median = ServerStatusHandler.median_sorted(sample)
            half = int(len(data) / 2)
            if len(data) % 2:
                q1 = (
                    ServerStatusHandler.median_sorted(
                        sample[:half]) +
                    ServerStatusHandler.median_sorted(
                        sample[:half + 1])
                ) / 2
                q3 = (
                    ServerStatusHandler.median_sorted(
                        sample[half:]) +
                    ServerStatusHandler.median_sorted(
                        sample[half + 1:])
                ) / 2
            else:
                q1 = ServerStatusHandler.median_sorted(
                    sample[:half])
                q3 = ServerStatusHandler.median_sorted(
                    sample[half:])

        return {
            "q1": median if q1 is None else q1,
            "median": median,
            "q3": median if q3 is None else q3
        }

    def get(self):
        if self.settings.app.response_log is None:
            raise tornado.web.HTTPError(404)

        response = {
            "1": 0,
            "2": 0,
            "3": 0,
            "4": 0,
            "5": 0,
        }
        duration = {
            "min": 0,
            "q1": 0,
            "median": 0,
            "q3": 0,
            "max": 0,
        }

        self.application.trim_response_log()

        min_ = None
        max_ = None

        for (
                _timestamp, status_code, duration_
        ) in self.settings.app.response_log:
            if min_ is None:
                min_ = duration_
                max_ = duration_
            else:
                min_ = min(min_, duration_)
                max_ = max(max_, duration_)

            k = str(status_code)[0]
            response[k] += 1

        if min_ is not None:
            duration["min"] = min_
            duration["max"] = max_
            try:
                duration.update(self.quartiles([
                    v[2] for v in self.settings.app.response_log]))
            except TypeError:
                sys.stderr.write(
                    "Failed quartiles: %s" %
                    repr([v[2] for v in self.settings.app.response_log]))
                sys.stderr.flush()
                raise

        label = self.application.title

        if self.settings.options.label:
            label = self.settings.options.label

        data = {
            "label": label,
            "response": response,
            "duration": duration,
        }

        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(json.dumps(data))



def init(application, defaults=None):
    define = tornado.options.define
    options = tornado.options.options

    defaults = dict(DEFAULTS, **(defaults or {}))

    define("host", type=str, default=defaults["host"],
           help="Run as the given host")
    define("port", type=int, default=defaults["port"],
           help="run on the given port")
    define("public_origin", default=None,
           help="Public origin (protocol, hostname and port)")

    define("ssl_cert", default=None, help="SSL certificate path")
    define("ssl_key", default=None, help="SSL private key path")

    define("status", type=bool, default=True,
           help="Enable stats on /server-stats")
    define("label", default=None, help="Label to include in stats")

    define("log", default=None,
           help="Log directory. Write permission required."
           "Logging is disabled if this option is not set.")

    tornado.options.parse_command_line()
    ssl_options = None
    if options.ssl_cert and options.ssl_key:
        ssl_options = {
            "certfile": options.ssl_cert,
            "keyfile": options.ssl_key,
        }
    http_server = tornado.httpserver.HTTPServer(
        application(),
        xheaders=True,
        ssl_options=ssl_options,
    )
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
