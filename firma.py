#!/usr/bin/env python3

import sys
import time
import json
import bisect
import datetime
import configparser

import tornado.web
import tornado.httpserver
import tornado.options
import tornado.ioloop
from tornado.log import app_log

from sqlalchemy.exc import OperationalError

DEFAULTS = {
    "port": 8000
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


class Application(tornado.web.Application):
    stats = None

    RESPONSE_LOG_DURATION = 5 * 60  # Seconds

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

    # Databases

    def mysql_attach_secondary(self, conf_path, db_name, query_string):
        if not self.settings.app.database:
            self.settings.app.database = {}
        db = self.settings.app.database

        database = conf_get(conf_path, "mysql", db_name, None)

        db[db_name] = {}
        db[db_name]["database"] = database
        db[db_name]["connected"] = False
        db[db_name]["status"] = None

        if database:
            try:
                self.orm.execute(query_string % database).scalar()
                self.mysql_db_success(db_name)
            except OperationalError as e:
                self.mysql_db_failure(db_name, e)

        self.add_stat("MySQL %s" % db_name, db[db_name]["status"])

    def mysql_db_success(self, db_name):
        db = self.settings.app.database
        if not db[db_name]["connected"]:
            app_log.info("Successfully connected to MySQL DB '%s'.", db_name)
        db[db_name]["connected"] = True
        db[db_name]["status"] = "Connected"

    def mysql_db_failure(self, db_name, error):
        db = self.settings.app.database
        if db[db_name].connected:
            app_log.warning("Lost connection to MySQL DB '%s'. %s", db_name, str(error))
        elif db[db_name].status is None:
            app_log.warning("Failed to connect to MySQL DB '%s'. %s", db_name, str(error))

        db[db_name]["connected"] = False
        if "denied" in str(error):
            db[db_name]["status"] = "Access denied"
        else:
            db[db_name]["status"] = "Cannot connect"

    def mysql_db_name(self, db_name):
        return self.settings.app.database and \
            self.settings.app.database[db_name] and \
            self.settings.app.database[db_name].database


    # Initialisation


    def init_settings(self, options):
        self.settings.options = options
        self.settings.app = {}

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

        if self.settings.options.status:
            handlers.insert(1, (r"/server-status", ServerStatusHandler))
            self.init_response_log(self.settings.app)

        _settings = self.settings
        # Resets `self.settings`:
        super(Application, self).__init__(handlers, **settings)
        self.settings = _settings
        self.write_stats()



class BaseHandler(tornado.web.RequestHandler):
    @property
    def settings(self):
        return self.application.settings

    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self.start = None
        sys.stdout.flush()

    def prepare(self):
        self.start = time.time()

    def on_finish(self):
        if not hasattr(self, "start") or self.start is None:
            return
        now = time.time()
        duration = now - self.start
        self.application.log_uri.info(
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

    define("port", type=int, default=defaults["port"],
           help="run on the given port")
    define("ssl_cert", default=None, help="SSL certificate path")
    define("ssl_key", default=None, help="SSL private key path")

    define("status", type=bool, default=True,
           help="Enable stats on /server-stats")
    define("label", default=None, help="Label to include in stats")

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
