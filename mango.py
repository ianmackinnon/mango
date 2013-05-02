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
from sqlalchemy.exc import SQLAlchemyError

from skin import skin

import mysql.mysql_init

from handle.base import BaseHandler, authenticated, sha1_concat
from handle.generate import GenerateMarkerHandler
from handle.auth import AuthRegisterHandler, \
    AuthLoginLocalHandler, AuthLoginGoogleHandler, \
    AuthVisitHandler, \
    AuthLogoutHandler
from handle.user import UserHandler, UserListHandler
from handle.home import HomeHandler
from handle.note import NoteHandler, NoteNewHandler, NoteListHandler, \
    NoteRevisionListHandler, NoteRevisionHandler
from handle.address import AddressHandler, \
    AddressRevisionListHandler, AddressRevisionHandler, \
    AddressEntityListHandler, \
    AddressLookupHandler, AddressNoteListHandler, AddressNoteHandler
from handle.org import OrgHandler, OrgNewHandler, \
    OrgRevisionListHandler, OrgRevisionHandler, \
    OrgListHandler, \
    OrgOrgaliasListHandler, \
    OrgOrgtagListHandler, OrgOrgtagHandler, \
    OrgNoteListHandler, OrgNoteHandler, \
    OrgAddressListHandler, OrgAddressHandler, \
    OrgEventHandler, OrgEventListHandler, \
    OrgListTaskAddressHandler, OrgListTaskVisibilityHandler
from handle.orgalias import OrgaliasHandler
from handle.event import EventHandler, EventNewHandler, \
    EventRevisionListHandler, EventRevisionHandler, \
    EventListHandler, \
    EventEventtagListHandler, EventEventtagHandler, EventNoteListHandler, \
    EventNoteHandler, EventAddressListHandler, EventAddressHandler, \
    EventDuplicateHandler, \
    EventOrgHandler, EventOrgListHandler, \
    DiaryHandler
from handle.orgtag import OrgtagHandler, OrgtagListHandler, \
    OrgtagNewHandler, OrgtagNoteListHandler, OrgtagNoteHandler
from handle.eventtag import EventtagHandler, EventtagListHandler, \
    EventtagNewHandler, EventtagNoteListHandler, EventtagNoteHandler
from handle.history import HistoryHandler
from handle.moderation import ModerationQueueHandler


define("port", default=8802, help="Run on the given port", type=int)
define("root", default='', help="URL root", type=unicode)
define("skin", default=True, help="Enable skin. 0 or 1. Default is 1.", type=bool)
define("database", default="sqlite", help="Either 'sqlite' or 'mysql'. Default is 'sqlite'.", type=str)
define("conf", default=".mango.conf", help="eg. .mango.conf", type=str)
define("log", default=None, help="Log directory. Write permission required. Logging is disabled if this option is not set.", type=unicode)



DEFAULT_CACHE_PERIOD = 60 * 60 * 8  # 8 hours



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

    session_cookie_name = "s"

    def load_cookie_secret(self):
        try:
            self.cookie_secret = open(".xsrf", "r").read().strip()
        except IOError as e:
            sys.stderr.write(
                "Could not open XSRF key. Run 'make .xsrf' to generate one.\n"
                )
            sys.exit(1)

    def path_is_authenticated(self, path):
        if path.startswith(self.url_root):
            path = "/" + path[len(self.url_root):]
        for row in self.handler_list:
            key, value = row[:2]
            if re.match(key, path) and hasattr(value, "get"):
                if hasattr(value.get, "authenticated") and \
                        value.get.authenticated == True:
                    return True
        return False

    def skin_variable(self, name):
        if not self.skin:
            return None

        def skin_key(key):
            return "skin:%s" % key

        value = self.cache.get(skin_key(name))
        if value:
            return value
        cache_period = 60 * 15;  # 15 minutes
        values = skin.variable(name) # May return multiple values.
        for key, value in values.items():
            self.cache.set(skin_key(key), value, cache_period)
        value = values.get(name, None)
        if not value:
            return
        return value
                
    def skin_variables(self, *args):
        variables = []
        for arg in args:
            variables.append(self.skin_variable(arg))
        return variables

            
        
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

        self.load_cookie_secret()

        def handle_id(text):
            return int(text)

        self.handlers = [
            (r"/", HomeHandler),
            (r'/static/image/map/marker/(.*)',
             GenerateMarkerHandler, {'path': "static/image/map/marker"}),
            (r'/(favicon.ico)',
             tornado.web.StaticFileHandler, {'path': "static"}),
            (r'/static/(.*)',
             tornado.web.StaticFileHandler, {'path': "static"}),

            (r"/user", UserListHandler),
            (r"/user/<id>", UserHandler),
            (r"/user/<self>", UserHandler),

            (r"/note", NoteListHandler),
            (r"/note/new", NoteNewHandler),
            (r"/note/<id>", NoteHandler),
            (r"/note/<id>/revision", NoteRevisionListHandler),
            (r"/note/<id>/revision/<id>",
             NoteRevisionHandler),

            (r"/organisation", OrgListHandler),
            (r"/organisation/new", OrgNewHandler),
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
            (r"/event/<id>/duplicate", EventDuplicateHandler),
            (r"/diary", DiaryHandler),

            (r"/task/address", OrgListTaskAddressHandler),
            (r"/task/visibility", OrgListTaskVisibilityHandler),

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

            (r"/auth/register", AuthRegisterHandler),
            (r"/auth/login", AuthLoginGoogleHandler),
            (r"/auth/login/google", AuthLoginGoogleHandler),
            (r"/auth/login/local", AuthLoginLocalHandler),
            (r"/auth/visit", AuthVisitHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/history", HistoryHandler),
            (r"/moderation/queue", ModerationQueueHandler),
            ]
        

        self.handlers = self.process_handlers(self.handlers)

        self.skin = options.skin

        self.url_root = options.root
        if not self.url_root.startswith('/'):
            self.url_root = '/' + self.url_root
        if not self.url_root.endswith('/'):
            self.url_root = self.url_root + '/'

        settings = dict(
            xsrf_cookies=True,
            cookie_secret=self.cookie_secret,
            login_url=self.url_root + "auth/login",
            )

        if options.database == "mysql":
            (database,
             app_username, app_password,
             admin_username, admin_password) = mysql.mysql_init.get_conf(options.conf)
            self.database_namespace = 'mysql://%s' % database
            connection_url = 'mysql://%s:%s@localhost/%s?charset=utf8' % (
                admin_username, admin_password, database)
        else:
            database = "mango.db"
            self.database_namespace = 'sqlite:///%s' % database
            connection_url = 'sqlite:///%s' % database

        engine = create_engine(
            connection_url,
            #echo=True,
            )

        if options.database == "mysql":
            self.database_mtime = datetime.datetime.utcnow()
        else:
            self.database_mtime = \
                datetime.datetime.utcfromtimestamp(
                os.path.getmtime(database))

        self.cache = RedisCache(
            self.cache_namespace(self.database_mtime.isoformat()))

        self.orm = scoped_session(sessionmaker(
                bind=engine,
                autocommit=False,
                query_cls=SafeQueryClass(),
                ))


        self.lookup = TemplateLookup(directories=['template'],
                                     input_encoding='utf-8',
                                     output_encoding='utf-8',
                                     default_filters=["unicode", "h"],
                                     )

        self.log_path = None
        self.log_handler = None
        if options.log:
            options.log = options.log.decode("utf-8")
            try:
                os.makedirs(options.log)
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise e

            self.log_path = os.path.join(
                options.log,
                'mango.log'
                )

            self.log_handler = logging.handlers.TimedRotatingFileHandler(
                self.log_path,
                when="midnight",
                encoding="utf-8",
                backupCount=7,
                utc=True
                )

        self.logger = logging.getLogger()
        if self.log_handler:
            self.logger.addHandler(self.log_handler)

        settings["xsrf_cookies"] = False
        
        tornado.web.Application.__init__(self, self.handlers, **settings)

        self.logger.info("""Mapping Application for NGOs (mango) running on port %d.""" % (options.port))
        

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()



if __name__ == "__main__":
    main()
