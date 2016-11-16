#!/usr/bin/env python3

import os
import re
import sys
import time
import errno
import bisect
import logging
import logging.handlers
import datetime

import redis

from mako.lookup import TemplateLookup

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

from sqlalchemy import create_engine, __version__ as sqlalchemy_version
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.query import Query
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from handle.base import \
    DefaultHandler, ServerStatusHandler, \
    sha1_concat
from handle.generate import GenerateMarkerHandler
from handle.markdown_safe import MarkdownSafeHandler
from handle.auth import AuthRegisterHandler, \
    AuthLoginLocalHandler, AuthLoginGoogleHandler, \
    AuthVisitHandler, \
    AuthLogoutHandler
from handle.user import UserHandler, UserListHandler
from handle.home import \
    NotFoundHandler, \
    HomeHandler, HomeOrgListHandler, HomeTargetListHandler, \
    DprteHandler, DprteOrgListHandler, DprteTargetListHandler, \
    DseiHandler, DseiOrgListHandler, DseiTargetListHandler, \
    FarnboroughHandler, FarnboroughOrgListHandler, \
    FarnboroughTargetListHandler, \
    SecurityPolicingHandler, SecurityPolicingOrgListHandler, \
    SecurityPolicingTargetListHandler
from handle.note import NoteHandler, NoteNewHandler, NoteListHandler, \
    NoteRevisionListHandler, NoteRevisionHandler
from handle.address import AddressHandler, \
    AddressRevisionListHandler, AddressRevisionHandler, \
    AddressEntityListHandler, \
    AddressLookupHandler, AddressNoteListHandler, AddressNoteHandler, \
    ModerationAddressNotFoundHandler
from handle.org import OrgHandler, OrgNewHandler, OrgSearchHandler, \
    OrgRevisionListHandler, OrgRevisionHandler, \
    OrgListHandler, \
    OrgOrgaliasListHandler, \
    OrgOrgtagListHandler, OrgOrgtagHandler, \
    OrgNoteListHandler, OrgNoteHandler, \
    OrgAddressListHandler, OrgAddressHandler, \
    OrgContactListHandler, OrgContactHandler, \
    OrgEventHandler, OrgEventListHandler, \
    ModerationOrgDescHandler, \
    ModerationOrgIncludeHandler
from handle.orgalias import OrgaliasHandler
from handle.event import EventHandler, EventNewHandler, \
    EventRevisionListHandler, EventRevisionHandler, \
    EventListHandler, \
    EventDuplicateHandler, \
    EventEventtagListHandler, EventEventtagHandler, \
    EventNoteListHandler, EventNoteHandler, \
    EventAddressListHandler, EventAddressHandler, \
    EventContactListHandler, EventContactHandler, \
    EventOrgHandler, EventOrgListHandler, \
    DiaryHandler
from handle.orgtag import OrgtagHandler, OrgtagListHandler, \
    OrgtagNewHandler, OrgtagNoteListHandler, OrgtagNoteHandler, \
    OrgtagActivityHandler, \
    ModerationOrgtagActivityHandler
from handle.eventtag import EventtagHandler, EventtagListHandler, \
    EventtagNewHandler, EventtagNoteListHandler, EventtagNoteHandler
from handle.contact import ContactHandler, \
    ContactRevisionListHandler, ContactRevisionHandler
from handle.history import HistoryHandler
from handle.moderation import ModerationQueueHandler

import conf

from model import connection_url_app, attach_search, engine_disable_mode
from model import Org



define("port", type=int, default=8802, help="Run on the given port")
define("root", default='', help="URL root")
define("skin", default="default", help="skin with the given style")
define("local", type=bool, default=False, help="Allow local authentication")
define("offsite", type=bool, default=None,
       help="Correct skin-specific links when offsite.")
define("events", type=bool, default=True, help="Enable events. Default is 1.")
define("verify_search", type=bool, default=True,
       help="Verify Elasticsearch data on startup. Default is 1.")
define("log", default=None,
       help="Log directory. Write permission required. Logging is disabled "
       "if this option is not set.")
define("status", default=True, help="Enable stats on /server-stats")
define("label", default=None, help="Label to include in stats")



FORWARDING_SERVER_LIST = [
    "127.0.0.1",
    ]

DEFAULT_CACHE_PERIOD = 60 * 60 * 8  # 8 hours

CONF_PATH = ".mango.conf"



class RedisCache(object):
    def __init__(self, namespace):
        super(RedisCache, self).__init__()
        self._cache = redis.StrictRedis()
        self.set_namespace(namespace)

    def set_namespace(self, namespace):
        self._namespace = namespace
        return self._namespace

    def get_namespace(self):
        return self._namespace

    def key(self, key):
        return self._namespace + ":" + key

    @property
    def name(self):
        return "redis"

    @property
    def connected(self):
        try:
            self._cache.ping()
        except (redis.ConnectionError, redis.exceptions.ResponseError):
            return False
        return True

    def get(self, key):
        try:
            value = self._cache.get(self.key(key))
        except (redis.ConnectionError, redis.exceptions.ResponseError):
            value = None
        if value:
            value = str(value, "utf-8")
        return value

    def set(self, key, value, period=DEFAULT_CACHE_PERIOD):
        try:
            self._cache.set(self.key(key), str(value))
            if period:
                self._cache.expire(self.key(key), period)
        except (redis.ConnectionError, redis.exceptions.ResponseError):
            pass

    def delete(self, key):
        try:
            self._cache.delete(self.key(key))
        except (redis.ConnectionError, redis.exceptions.ResponseError):
            pass



def SafeQueryClass(retry=3):
    # pylint: disable=invalid-name
    # Allow `SafeQueryClass` factory function.

    class SafeQuery(Query):
        def __init__(self, entities, session=None):
            Query.__init__(self, entities, session)
            self._retry = retry

        def __iter__(self):
            tries = self._retry
            while True:
                try:
                    results = list(Query.__iter__(self))
                    break
                except SQLAlchemyError as e:
                    if tries:
                        self.session.rollback()
                        tries -= 1
                        continue
                    raise e
            return iter(results)

    return SafeQuery



def url_type_id(text):
    value = int(text)
    assert value > 0
    return value



class Application(tornado.web.Application):
    name = "mango"
    title = "Mapping Application for NGOs (Mango)"
    sqlite_path = "mango.db"
    max_age = 86400 * 365 * 10  # 10 years

    RESPONSE_LOG_DURATION = 5 * 60  # Seconds

    def load_cookie_secret(self):
        try:
            with open(".xsrf", "r", encoding="utf-8") as fp:
                self.cookie_secret = fp.read().strip()
        except IOError:
            sys.stderr.write(
                "Could not open XSRF key. Run 'make .xsrf' to generate one.\n"
                )
            sys.exit(1)

    def cache_namespace(self, offset=""):
        hash_ = sha1_concat(
            sys.version,
            sqlalchemy_version,
            self.database_namespace,
            str(offset),
            )
        namespace = "%s:%s" % (self.name, hash_[:7])
        return namespace

    url_parsers = {
        "id": ("[1-9][0-9]*", url_type_id),
        "self": ("self", None),
        }

    @staticmethod
    def process_handlers(handlers):
        regex_handlers = []
        for handler in handlers:
            regex, handler, kwargs = (handler + (None, ))[:3]
            regex = re.split(r"(<\w+>)", regex)
            for i in range(1, len(regex), 2):
                type_ = regex[i][1:-1]
                url_regex, url_type = Application.url_parsers[type_]
                regex[i] = r"(%s)" % url_regex
                if not kwargs:
                    kwargs = {}
                if "types" not in kwargs:
                    kwargs["types"] = []
                kwargs["types"].append(url_type)
            regex = "".join(regex)
            regex_handlers.append((regex, handler, kwargs))
        return regex_handlers

    def increment_cache(self):
        offset = datetime.datetime.utcnow().isoformat()
        namespace = self.cache_namespace(offset)
        self.cache.set_namespace(namespace)

    def init_response_log(self):
        self.response_log = []
        tornado.ioloop.PeriodicCallback(
            self.trim_response_log,
            self.RESPONSE_LOG_DURATION * 1000
        ).start()

    @tornado.gen.coroutine
    def trim_response_log(self):
        start = time.time() - self.RESPONSE_LOG_DURATION
        row = [start, None, None]
        index = bisect.bisect(self.response_log, row)
        self.response_log = self.response_log[index:]

    def __init__(self):
        self.response_log = None
        self.cache_log = None

        self.events = options.events

        self.handlers = [
            (r"/", HomeHandler),

            (r"/home", HomeHandler),
            (r"/home-org", HomeOrgListHandler),
            (r"/home-target", HomeTargetListHandler),
            (r"/dprte", DprteHandler),
            (r"/dprte-org", DprteOrgListHandler),
            (r"/dprte-target", DprteTargetListHandler),
            (r"/dsei", DseiHandler),
            (r"/dsei-org", DseiOrgListHandler),
            (r"/dsei-target", DseiTargetListHandler),
            (r"/farnborough", FarnboroughHandler),
            (r"/farnborough-org", FarnboroughOrgListHandler),
            (r"/farnborough-target", FarnboroughTargetListHandler),
            (r"/security-and-policing", SecurityPolicingHandler),
            (r"/security-and-policing-org", SecurityPolicingOrgListHandler),
            (r"/security-and-policing-target",
             SecurityPolicingTargetListHandler),
            (r"/activity-tags", OrgtagActivityHandler),

            (r'/static/image/map/marker/(.*)',
             GenerateMarkerHandler, {'path': "static/image/map/marker"}),
            (r'/(favicon.ico)',
             tornado.web.StaticFileHandler, {'path': "static"}),
            (r'/static/(.*)',
             tornado.web.StaticFileHandler, {'path': "static"}),

            (r"/auth/register", AuthRegisterHandler),
            (r"/auth/login", AuthLoginGoogleHandler),
            (r"/auth/login/google", AuthLoginGoogleHandler),
            (r"/auth/login/local", AuthLoginLocalHandler),
            (r"/auth/visit", AuthVisitHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/history", HistoryHandler),

            (r"/moderation/queue", ModerationQueueHandler),
            (r"/moderation/organisation-description",
             ModerationOrgDescHandler),
            (r"/moderation/organisation-inclusion",
             ModerationOrgIncludeHandler),
            (r"/moderation/organisation-tag-activity",
             ModerationOrgtagActivityHandler),
            (r"/moderation/address-not-found",
             ModerationAddressNotFoundHandler),

            (r"/user", UserListHandler),
            (r"/user/<id>", UserHandler),
            (r"/user/<self>", UserHandler),

            (r"/organisation", OrgListHandler),
            (r"/organisation/new", OrgNewHandler),
            (r"/organisation/search", OrgSearchHandler),
            (r"/organisation/<id>", OrgHandler),
            (r"/organisation/<id>/revision", OrgRevisionListHandler),
            (r"/organisation/<id>/revision/<id>",
             OrgRevisionHandler),
            (r"/organisation/<id>/tag", OrgOrgtagListHandler),
            (r"/organisation/<id>/tag/<id>", OrgOrgtagHandler),
            (r"/organisation/<id>/alias", OrgOrgaliasListHandler),
            (r"/organisation/<id>/note", OrgNoteListHandler),
            (r"/organisation/<id>/note/<id>", OrgNoteHandler),
            (r"/organisation/<id>/address", OrgAddressListHandler),
            (r"/organisation/<id>/address/<id>",
             OrgAddressHandler),
            (r"/organisation/<id>/event", OrgEventListHandler),
            (r"/organisation/<id>/event/<id>",
             OrgEventHandler),
            (r"/organisation/<id>/contact", OrgContactListHandler),
            (r"/organisation/<id>/contact/<id>",
             OrgContactHandler),

            (r"/organisation-alias/<id>", OrgaliasHandler),

            (r"/event", EventListHandler),
            (r"/event/new", EventNewHandler),

            (r"/event/<id>", EventHandler),

            (r"/event/<id>/revision", EventRevisionListHandler),
            (r"/event/<id>/revision/<id>",
             EventRevisionHandler),
            (r"/event/<id>/tag", EventEventtagListHandler),
            (r"/event/<id>/tag/<id>",
             EventEventtagHandler),
            (r"/event/<id>/note", EventNoteListHandler),
            (r"/event/<id>/note/<id>", EventNoteHandler),
            (r"/event/<id>/address", EventAddressListHandler),
            (r"/event/<id>/address/<id>",
             EventAddressHandler),
            (r"/event/<id>/organisation", EventOrgListHandler),
            (r"/event/<id>/organisation/<id>",
             EventOrgHandler),
            (r"/event/<id>/contact", EventContactListHandler),
            (r"/event/<id>/contact/<id>",
             EventContactHandler),
            (r"/event/<id>/duplicate", EventDuplicateHandler),
            (r"/diary", DiaryHandler),

            (r"/address", AddressEntityListHandler),
            (r"/address/lookup", AddressLookupHandler),
            (r"/address/<id>/revision",
             AddressRevisionListHandler),
            (r"/address/<id>/revision/<id>",
             AddressRevisionHandler),
            (r"/address/<id>", AddressHandler),
            (r"/address/<id>/note", AddressNoteListHandler),
            (r"/address/<id>/note/<id>",
             AddressNoteHandler),

            (r"/organisation-tag", OrgtagListHandler),
            (r"/organisation-tag/new", OrgtagNewHandler),
            (r"/organisation-tag/<id>", OrgtagHandler),
            (r"/organisation-tag/<id>/note", OrgtagNoteListHandler),
            (r"/organisation-tag/<id>/note/<id>", OrgtagNoteHandler),

            (r"/event-tag", EventtagListHandler),
            (r"/event-tag/new", EventtagNewHandler),
            (r"/event-tag/<id>", EventtagHandler),
            (r"/event-tag/<id>/note", EventtagNoteListHandler),
            (r"/event-tag/<id>/note/<id>",
             EventtagNoteHandler),

            (r"/contact/<id>/revision",
             ContactRevisionListHandler),
            (r"/contact/<id>/revision/<id>",
             ContactRevisionHandler),
            (r"/contact/<id>", ContactHandler),

            (r"/note", NoteListHandler),
            (r"/note/new", NoteNewHandler),
            (r"/note/<id>", NoteHandler),
            (r"/note/<id>/revision", NoteRevisionListHandler),
            (r"/note/<id>/revision/<id>",
             NoteRevisionHandler),

            (r"/api/markdown-safe", MarkdownSafeHandler),

            (r"/.*", NotFoundHandler),
        ]

        self.label = options.label

        if options.status:
            self.handlers.insert(1, (r"/server-status", ServerStatusHandler))
            self.init_response_log()

        if not self.events:
            self.handlers = [v for v in self.handlers if (
                "/event" not in v[0] and
                "/diary" not in v[0])]

        self.handlers = self.process_handlers(self.handlers)

        settings = dict()

        # Authentication & Cookies

        settings["google_oauth"] = {
            "key": conf.get(CONF_PATH, 'google-oauth', 'client-id'),
            "secret": conf.get(CONF_PATH, 'google-oauth', 'client-secret'),
            "default_handler_class": DefaultHandler,
        }

        settings["google_maps"] = {
            "api_key": conf.get(CONF_PATH, 'google-maps', 'api-key'),
        }

        self.load_cookie_secret()
        settings.update(dict(
            xsrf_cookies=True,
            cookie_secret=self.cookie_secret,
        ))

        self.local_auth = options.local
        self.cookie_prefix = conf.get(CONF_PATH, "app", "cookie-prefix")

        # Database & Cache

        mysql_database = conf.get(CONF_PATH, "mysql", "database")
        self.database_namespace = 'mysql://%s' % mysql_database

        self.cache = RedisCache(
            self.cache_namespace(datetime.datetime.utcnow().isoformat()))

        connection_url = connection_url_app()
        engine = create_engine(
            connection_url,
            pool_recycle=7200  # Expire connections after 2 hours
        )                      # (MySQL disconnects unilaterally after 8)

        engine_disable_mode(engine, "ONLY_FULL_GROUP_BY")
        self.orm = scoped_session(sessionmaker(
            bind=engine,
            autocommit=False,
            query_cls=SafeQueryClass(),
        ))

        try:
            self.orm.query(Org).first()
        except OperationalError as e:
            sys.stderr.write(
                "Cannot connect to MySQL database %s.\n" % mysql_database)
            sys.exit(1)

        attach_search(engine, self.orm, verify=options.verify_search)
        self.orm.remove()

        self.cache.state = self.cache.connected and "active" or "inactive"

        # Logging

        self.log_path_uri = None
        self.log_uri = logging.getLogger('%s.uri' % self.name)
        self.log_uri.propagate = False
        self.log_uri.setLevel(logging.INFO)
        if options.log:
            try:
                os.makedirs(options.log)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise e

            self.log_uri_path = os.path.join(
                options.log,
                '%s.uri.log' % self.name
                )

            self.log_uri.addHandler(
                logging.handlers.TimedRotatingFileHandler(
                    self.log_uri_path,
                    when="midnight",
                    encoding="utf-8",
                    backupCount=7,
                    utc=True
                    )
                )
        else:
            self.log_uri.addHandler(logging.NullHandler())

        # Skin & Templates

        try:
            self.skin = __import__("skin.%s" % (options.skin),
                                   globals(), locals(), ["load"])
        except ImportError as e:
            sys.stdout.write("Fatal: Skin '%s' not found.\n" % options.skin)
            sys.exit(1)

        self.offsite = options.offsite

        self.lookup = TemplateLookup(
            directories=['template'],
            input_encoding='utf-8',
            output_encoding='utf-8',
            default_filters=["unicode", "h"],
            )

        # HTTP Server

        self.forwarding_server_list = FORWARDING_SERVER_LIST

        self.settings = settings

        tornado.web.Application.__init__(self, self.handlers, **settings)

        stats = {
            "Label": self.label,
            "Address": "http://localhost:%d" % options.port,
            "Database": "MySQL: %s" % mysql_database,
            "Cache": "%s (%s) %s" % (self.cache.name, self.cache.state,
                                     self.cache.get_namespace()),
            "Skin": options.skin,
            "Events": self.events and "Enabled" or "Disabled",
            "Started": datetime.datetime.utcnow() \
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        sys.stdout.write("%s is running.\n" % self.title)
        for key, value in list(stats.items()):
            sys.stdout.write("  %-20s %s\n" % (key + ":", value))
        sys.stdout.flush()


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(
        Application(),
        xheaders=True,
    )
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()



if __name__ == "__main__":
    main()
