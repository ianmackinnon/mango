#!/usr/bin/env python3

import re
import sys
import datetime

import redis

from mako.lookup import TemplateLookup

import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options

from sqlalchemy import create_engine, __version__ as sqlalchemy_version
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.query import Query
from sqlalchemy.exc import SQLAlchemyError, OperationalError

import firma

from handle.base import \
    DefaultHandler, \
    sha1_concat
from handle.generate import GenerateMarkerHandler
from handle.markdown_safe import MarkdownSafeHandler
from handle.auth import AuthRegisterHandler, \
    AuthLoginPasswordHandler, AuthLoginGoogleHandler, \
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
    SecPolHandler, SecPolOrgListHandler, \
    SecPolTargetListHandler
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
    ApiSummaryOrgHandler, \
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

from model import mysql, Org, attach_search
from model import CONF_PATH, DATABASE_NAMES



DEFAULT_PORT = 8802



define("root", default='', help="URL root")
define("skin", default="default", help="skin with the given style")
define("local", type=bool, default=False, help="Allow local authentication")
define("offsite", type=bool, default=None,
       help="Correct skin-specific links when offsite.")
define("events", type=bool, default=True, help="Enable events. Default is 1.")
define("verify_search", type=bool, default=True,
       help="Verify Elasticsearch data on startup. Default is 1.")



FORWARDING_SERVER_LIST = [
    "127.0.0.1",
    ]

DEFAULT_CACHE_PERIOD = 60 * 60 * 8  # 8 hours



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



class MangoApplication(firma.Application):
    name = "mango"
    title = "Mapping Application for NGOs (Mango)"
    sqlite_path = "mango.db"
    max_age = 86400 * 365 * 10  # 10 years

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
                url_regex, url_type = MangoApplication.url_parsers[type_]
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

    def __init__(self):
        self.orm = None
        self.cache = None
        self.cache_log = None
        self.database_namespace = None
        self.skin = None
        self.offsite = None
        self.lookup = None

        self.events = options.events

        handlers = [
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
            (r"/security-and-policing", SecPolHandler),
            (r"/security-and-policing-org", SecPolOrgListHandler),
            (r"/security-and-policing-target",
             SecPolTargetListHandler),
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
            (r"/auth/login/password", AuthLoginPasswordHandler),
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

            (r"/api/summary/org/<id>", ApiSummaryOrgHandler),

            (r"/.*", NotFoundHandler),
        ]

        if not self.events:
            handlers = [v for v in handlers if (
                "/event" not in v[0] and
                "/diary" not in v[0])]

        handlers = self.process_handlers(handlers)

        settings = dict()

        # Authentication

        settings["google_oauth"] = {
            "key": firma.conf_get(
                CONF_PATH, 'google-oauth', 'client-id'),
            "secret": firma.conf_get(
                CONF_PATH, 'google-oauth', 'client-secret'),
            "default_handler_class": DefaultHandler,
        }

        settings["google_maps"] = {
            "api_key": firma.conf_get(CONF_PATH, 'google-maps', 'api-key'),
        }

        self.local_auth = options.local

        # HTTP Server

        self.forwarding_server_list = FORWARDING_SERVER_LIST

        super(MangoApplication, self).__init__(
            handlers, options, **settings)


    def init_skin(self):
        try:
            self.skin = __import__("skin.%s" % (options.skin),
                                   globals(), locals(), ["load"])
        except ImportError:
            sys.stdout.write("Fatal: Skin '%s' not found.\n" % options.skin)
            sys.exit(1)

        self.offsite = options.offsite

        self.add_stat("Skin", options.skin)


    def init_templates(self):
        self.lookup = TemplateLookup(
            directories=['template'],
            input_encoding='utf-8',
            output_encoding='utf-8',
            default_filters=["unicode", "h"],
        )


    def init_database(self):
        # Main Database and Cache

        conf = mysql.get_conf(CONF_PATH)

        self.database_namespace = 'mysql://%s' % conf.database
        self.cache = RedisCache(
            self.cache_namespace(datetime.datetime.utcnow().isoformat()))

        signature = "%s@%s" % (conf.app_username, conf.database)
        connection_url = mysql.connection_url_app(CONF_PATH)

        engine = create_engine(
            connection_url,
            pool_recycle=3600  # Expire connections after 1 hours
        )                      # (MySQL disconnects unilaterally after 8)

        mysql.engine_disable_mode(engine, "ONLY_FULL_GROUP_BY")

        self.orm = scoped_session(sessionmaker(
            bind=engine,
            autocommit=False,
            query_cls=SafeQueryClass(),
        ))

        try:
            self.orm.query(Org).first()
        except OperationalError:
            sys.stderr.write(
                "Cannot connect to database %s.\n" % signature)
            sys.exit(1)
        attach_search(engine, self.orm, verify=options.verify_search)
        self.orm.remove()

        self.add_stat("MySQL", "Connected (%s)" % signature)

        self.add_stat("Cache", "%s (%s) %s" % (
            self.cache.name,
            self.cache.connected and "active" or "inactive",
            self.cache.get_namespace()
        ))

        # Secondary Databases

        self.mysql_attach_secondary(
            "influence",
            mysql.replace_database_names(DATABASE_NAMES, "influence"),
            "select count(org_id) from %s.org")

        self.mysql_attach_secondary(
            "company-exports",
            mysql.replace_database_names(DATABASE_NAMES, "company-exports"),
            "select count(company_id) from %s.company")



    def init_settings(self, options):
        # pylint: disable=redefined-outer-name
        # Receiving `options` from parent.
        "Update `settings` in place and add rows to `self.stats`."

        super(MangoApplication, self).init_settings(options)

        self.init_database()
        self.init_skin()
        self.init_templates()
        self.init_cookies(firma.conf_get(CONF_PATH, 'app', 'cookie-prefix'))

        self.add_stat("Events", self.events and "Enabled" or "Disabled")



if __name__ == "__main__":
    firma.init(MangoApplication, {
        "port": DEFAULT_PORT
    })
