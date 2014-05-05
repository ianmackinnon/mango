#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import errno
import redis
import logging
import logging.handlers
import datetime
import memcache

from mako.template import Template
from mako.lookup import TemplateLookup

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import escape
from tornado.options import define, options

from sqlalchemy import create_engine, __version__ as sqlalchemy_version
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.query import Query
from sqlalchemy.exc import SQLAlchemyError, OperationalError

import mysql.mysql_init

from handle.base import BaseHandler, authenticated, sha1_concat
from handle.generate import GenerateMarkerHandler
from handle.auth import AuthRegisterHandler, \
    AuthLoginLocalHandler, AuthLoginGoogleHandler, \
    AuthVisitHandler, \
    AuthLogoutHandler
from handle.user import UserHandler, UserListHandler
from handle.home import HomeHandler, HomeOrgListHandler, \
    DseiHandler, DseiOrgListHandler, \
    FarnboroughHandler, FarnboroughOrgListHandler, \
    CountryTagListHandler
from handle.note import NoteHandler, NoteNewHandler, NoteListHandler, \
    NoteRevisionListHandler, NoteRevisionHandler
from handle.address import AddressHandler, \
    AddressRevisionListHandler, AddressRevisionHandler, \
    AddressEntityListHandler, \
    AddressLookupHandler, AddressNoteListHandler, AddressNoteHandler
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
    OrgtagNewHandler, OrgtagNoteListHandler, OrgtagNoteHandler
from handle.eventtag import EventtagHandler, EventtagListHandler, \
    EventtagNewHandler, EventtagNoteListHandler, EventtagNoteHandler
from handle.contact import ContactHandler, \
    ContactRevisionListHandler, ContactRevisionHandler
from handle.history import HistoryHandler
from handle.moderation import ModerationQueueHandler

import conf
from model import get_database, connection_url_app, attach_search
from model import Org, Orgtag, Orgalias, Event, Eventtag, Address, Note
from model_v import Org_v, Event_v, Address_v, Note_v



define("port", default=8802, help="Run on the given port", type=int)
define("root", default='', help="URL root", type=unicode)
define("skin", default=u"default", help="skin with the given style", type=unicode)
define("log", default=None, help="Log directory. Write permission required. Logging is disabled if this option is not set.", type=unicode)



forwarding_server_list = [
    "127.0.0.1",
    ]

DEFAULT_CACHE_PERIOD = 60 * 60 * 8  # 8 hours

conf_path = ".mango.conf"



class BaseCache(object): 
    def set_namespace(self, namespace):
        self._namespace = namespace
        return self._namespace

    def key(self, key):
        return self._namespace + ":" + key
    


class DictCache(BaseCache):
    def __init__(self, namespace):
        self._cache = {}
        
    def get(self, key):
        return self._cache.get(key, None)

    def set(self, key, value, period=None):
        # Does not support expiration
        self._cache[key] = value

    def delete(self, key):
        del self._cache[key]



class MemcacheCache(BaseCache):
    def __init__(self, namespace):
        self._cache = memcache.Client(["127.0.0.1:11211"])
        self.set_namespace(namespace)
        
    @property
    def name(self):
        return "memcache"
        
    @property
    def connected(self):
        return bool(self._cache.get_stats())

    def get(self, key):
        value = self._cache.get(self.key(key))
        return value

    def set(self, key, value, period=DEFAULT_CACHE_PERIOD):
        if not period:
            period = 0;
        self._cache.set(self.key(key), value, time=period)

    def delete(self, key):
        self._cache.delete(self.key(key))



class RedisCache(BaseCache):
    def __init__(self, namespace):
        self._cache = redis.StrictRedis(host='localhost', port=6379, db=0)
        self.set_namespace(namespace)

    @property
    def name(self):
        return "redis"
        
    @property
    def connected(self):
        try:
            self._cache.ping()
        except redis.ConnectionError as e:
            return False
        return True
        
    def get(self, key):
        try:
            value = self._cache.get(self.key(key))
        except redis.ConnectionError as e:
            value = None
        if value:
            value = unicode(value, "utf-8")
        return value

    def set(self, key, value, period=DEFAULT_CACHE_PERIOD):
        try:
            self._cache.set(self.key(key), unicode(value))
            if period:
                self._cache.expire(self.key(key), period)
        except redis.ConnectionError as e:
            pass

    def delete(self, key):
        try:
            self._cache.delete(self.key(key))
        except redis.ConnectionError as e:
            pass



def SafeQueryClass(retry=3):
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

    name = u"mango"
    title = u"Mapping Application for NGOs (Mango)"
    sqlite_path = u"mango.db"
    max_age = 86400 * 365 * 10  # 10 years

    session_cookie_name = "s"

    def load_cookie_secret(self):
        try:
            self.cookie_secret = open(".xsrf", "r").read().strip()
        except IOError as e:
            sys.stderr.write(
                "Could not open XSRF key. Run 'make .xsrf' to generate one.\n"
                )
            sys.exit(1)

    def cache_namespace(self, offset=""):
        return sha1_concat(
            sys.version,
            sqlalchemy_version,
            self.database_namespace,
            offset,
            )

    url_parsers = {
        "id": ("[1-9][0-9]*", url_type_id),
        "self": ("self", None),
        }

    @staticmethod
    def process_handlers(handlers):
        regex_handlers = []
        for handler in handlers:
            regex, handler, kwargs = (handler + (None, ))[:3]
            regex = re.split("(<\w+>)", regex)
            for i in range(1, len(regex), 2):
                type_ = regex[i][1:-1]
                url_regex, url_type = Application.url_parsers[type_]
                regex[i] = r"(%s)" % url_regex
                if not kwargs:
                    kwargs = {}
                if not "types" in kwargs:
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
        def handle_id(text):
            return int(text)

        self.handlers = [
            (r"/", HomeHandler),
            (r"/home-org", HomeOrgListHandler),
            (r"/dsei", DseiHandler),
            (r"/dsei-org", DseiOrgListHandler),
            (r"/farnborough", FarnboroughHandler),
            (r"/farnborough-org", FarnboroughOrgListHandler),
            (r"/country-tag", CountryTagListHandler),

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
            ]
        
        self.handlers = self.process_handlers(self.handlers)

        settings = {
#            "static_path": os.path.join(os.path.dirname(__file__), "static"),
            }

        # Authentication & Cookies

        self.load_cookie_secret()
        settings.update(dict(
            xsrf_cookies=True,
            cookie_secret=self.cookie_secret,
            ))

        # Database & Cache

        database = get_database()
        if database == "mysql":
            mysql_database = conf.get(conf_path, u"mysql", u"database")
            self.database_namespace = 'mysql://%s' % mysql_database
            self.database_mtime = datetime.datetime.utcnow()
        elif database == "sqlite":
            sqlite_database = self.sqlite_path
            self.database_namespace = 'sqlite:///%s' % sqlite_database
            self.database_mtime = datetime.datetime.utcfromtimestamp(
                os.path.getmtime(sqlite_database))
            
        self.cache = RedisCache(
            self.cache_namespace(self.database_mtime.isoformat()))

        connection_url = connection_url_app()
        engine = create_engine(connection_url,)
        self.orm = scoped_session(sessionmaker(
                bind=engine,
                autocommit=False,
                query_cls=SafeQueryClass(),
                ))
        try:
            self.orm.query(Org).first()
        except OperationalError as e:
            sys.stderr.write("Cannot connect to database %s.\n" % database)
            sys.exit(1)
            
        attach_search(engine, self.orm)

        # Logging

        self.log_path_uri = None
        self.log_uri = logging.getLogger(u'%s.uri' % self.name)
        self.log_uri.propagate = False
        self.log_uri.setLevel(logging.INFO)
        if options.log:
            options.log = options.log.decode("utf-8")
            try:
                os.makedirs(options.log)
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise e

            self.log_uri_path = os.path.join(
                options.log,
                u'%s.uri.log' % self.name
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

        self.lookup = TemplateLookup(
            directories=['template'],
            input_encoding='utf-8',
            output_encoding='utf-8',
            default_filters=["unicode", "h"],
            )

        # HTTP Server

        self.forwarding_server_list = forwarding_server_list

        tornado.web.Application.__init__(self, self.handlers, **settings)

        sys.stdout.write(u"""%s is running.
  Address:   http://localhost:%d
  Database:  %s
  Cache:     %s (%s)
""" % (
                self.title,
                options.port,
                database,
                self.cache.name,
                self.cache.connected and "active" or "inactive",
                ))
        sys.stdout.flush()
        


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()



if __name__ == "__main__":
    main()
