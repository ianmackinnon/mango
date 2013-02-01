#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import errno
import urllib
import logging
import memcache

from BeautifulSoup import BeautifulSoup

from mako.template import Template
from mako.lookup import TemplateLookup

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

from sqlalchemy import create_engine, __version__ as sqlalchemy_version
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.query import Query
from sqlalchemy.exc import SQLAlchemyError

import mysql.mysql_init

from handle.base import BaseHandler, authenticated, sha1_concat
from handle.generate import GenerateMarkerHandler
from handle.auth import AuthLoginHandler, AuthLoginLocalHandler, \
    AuthLoginGoogleHandler, AuthLogoutHandler
from handle.user import UserHandler, UserListHandler
from handle.home import HomeHandler
from handle.note import NoteHandler, NoteNewHandler, NoteListHandler
from handle.address import AddressHandler, AddressListHandler, \
    AddressLookupHandler, AddressNoteListHandler, AddressNoteHandler
from handle.org import OrgHandler, OrgNewHandler, OrgListHandler, \
    OrgOrgaliasListHandler, \
    OrgOrgtagListHandler, OrgOrgtagHandler, \
    OrgNoteListHandler, OrgNoteHandler, \
    OrgAddressListHandler, OrgAddressHandler, \
    OrgListTaskAddressHandler, OrgListTaskVisibilityHandler
from handle.orgalias import OrgaliasHandler
from handle.event import EventHandler, EventNewHandler, EventListHandler, \
    EventEventtagListHandler, EventEventtagHandler, EventNoteListHandler, \
    EventNoteHandler, EventAddressListHandler, EventAddressHandler
from handle.orgtag import OrgtagHandler, OrgtagListHandler, \
    OrgtagNewHandler, OrgtagNoteListHandler, OrgtagNoteHandler
from handle.eventtag import EventtagHandler, EventtagListHandler, \
    EventtagNewHandler, EventtagNoteListHandler, EventtagNoteHandler
from handle.history import HistoryHandler



define("port", default=8802, help="Run on the given port", type=int)
define("root", default='', help="URL root", type=str)
define("caat", default=False, help="CAAT header", type=bool)
define("database", default="sqlite", help="sqlite or mysql", type=str)
define("conf", default=".mango.conf", help="eg. .mango.conf", type=str)



class DictCache(object):
    def __init__(self, namespace):
        self._cache = {}
        
    def get(self, key):
        return self._cache.get(key, None)

    def set(self, key, value):
        self._cache[key] = value

    def delete(self, key):
        del self._cache[key]



class MemcacheCache(object):
    def __init__(self, namespace):
        self._cache = memcache.Client(["127.0.0.1:11211"])
        self._namespace = namespace
        
    def key(self, key):
        return self._namespace + ":" + key
        
    def get(self, key):
        return self._cache.get(self.key(key))

    def set(self, key, value, period=15*60):  # 15 minutes
        self._cache.set(self.key(key), value, time=period)

    def delete(self, key):
        self._cache.delete(self.key(key))



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
                
        
    def caat_header_footer(self):
        header1 = self.cache.get("header1")
        header2 = self.cache.get("header2")
        footer = self.cache.get("footer")
        if header1 and header2 and footer:
            return header1, header2, footer

        caat_source = "render-header-footer.php"
        caat_uri = "http://www.caat.org.uk/resources/mapping/render-header-footer.php"
        caat_period = 15 * 60 # 15 minutes
        
        page = urllib.urlopen(caat_uri).read()
        soup = BeautifulSoup(page)
 
        regex = re.compile("^[/]")
        for link in soup.findAll(href=regex):
            link["href"] = "http://www.caat.org.uk" + link["href"]
        for link in soup.findAll(src=regex):
            link["src"] = "http://www.caat.org.uk" + link["src"]
 
        text = unicode(soup)

        text = text.replace("<head>",
                     """
<head>
  <!--[if lt IE 9]>
  <script src="//html5shiv.googlecode.com/svn/trunk/html5.js"></script>
  <![endif]-->

""")

        splitter_1 = '</head>'
        splitter_2 = '<div id="mapping">'

        assert splitter_2 in text

        header, footer = text.split(splitter_2)
        header += splitter_2

        assert splitter_1 in header

        header1, header2 = header.split(splitter_1)
        header2 = splitter_1 + header2

        del header

        self.cache.set("header1", header1, caat_period)
        self.cache.set("header2", header2, caat_period)
        self.cache.set("footer", footer, caat_period)

        return header1, header2, footer



    def __init__(self):

        self.load_cookie_secret()

        re_id = "([1-9][0-9]*)"

        self.handler_list = [
            (r"/", HomeHandler),
            (r'/static/image/map/marker/(.*)',
             GenerateMarkerHandler, {'path': "static/image/map/marker"}),
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': "static"}),

            (r"/user", UserListHandler),
            (r"/user/%s" % re_id , UserHandler),

            (r"/note", NoteListHandler),
            (r"/note/new", NoteNewHandler),
            (r"/note/%s" % re_id, NoteHandler),

            (r"/organisation", OrgListHandler),
            (r"/organisation/new", OrgNewHandler),
            (r"/organisation/%s" % re_id, OrgHandler),
            (r"/organisation/%s/tag" % re_id, OrgOrgtagListHandler),
            (r"/organisation/%s/tag/%s" % (re_id, re_id), OrgOrgtagHandler),
            (r"/organisation/%s/alias" % re_id, OrgOrgaliasListHandler),
            (r"/organisation/%s/note" % re_id, OrgNoteListHandler),
            (r"/organisation/%s/note/%s" % (re_id, re_id), OrgNoteHandler),
            (r"/organisation/%s/address" % re_id, OrgAddressListHandler),
            (r"/organisation/%s/address/%s" % (re_id, re_id),
             OrgAddressHandler),

            (r"/organisation-alias/%s" % re_id, OrgaliasHandler),

            (r"/event", EventListHandler),
            (r"/event/new", EventNewHandler),
            (r"/event/%s" % re_id, EventHandler),
            (r"/event/%s/tag" % re_id, EventEventtagListHandler),
            (r"/event/%s/tag/%s" % (re_id, re_id), EventEventtagHandler),
            (r"/event/%s/note" % re_id, EventNoteListHandler),
            (r"/event/%s/note/%s" % (re_id, re_id), EventNoteHandler),
            (r"/event/%s/address" % re_id, EventAddressListHandler),
            (r"/event/%s/address/%s" % (re_id, re_id),
             EventAddressHandler),

            (r"/task/address", OrgListTaskAddressHandler),
            (r"/task/visibility", OrgListTaskVisibilityHandler),

            (r"/address", AddressListHandler),
            (r"/address/lookup", AddressLookupHandler),
            (r"/address/%s" % re_id, AddressHandler),
            (r"/address/%s/note" % re_id, AddressNoteListHandler),
            (r"/address/%s/note/%s" % (re_id, re_id), AddressNoteHandler),

            (r"/organisation-tag", OrgtagListHandler),
            (r"/organisation-tag/new", OrgtagNewHandler),
            (r"/organisation-tag/%s" % re_id, OrgtagHandler),
            (r"/organisation-tag/%s/note" % re_id, OrgtagNoteListHandler),
            (r"/organisation-tag/%s/note/%s" % (re_id, re_id), OrgtagNoteHandler),

            (r"/event-tag", EventtagListHandler),
            (r"/event-tag/new", EventtagNewHandler),
            (r"/event-tag/%s" % re_id, EventtagHandler),
            (r"/event-tag/%s/note" % re_id, EventtagNoteListHandler),
            (r"/event-tag/%s/note/%s" % (re_id, re_id), EventtagNoteHandler),

            (r"/auth/login", AuthLoginGoogleHandler),
            (r"/auth/login/google", AuthLoginGoogleHandler),
            (r"/auth/login/local", AuthLoginLocalHandler),
            (r"/auth/logout", AuthLogoutHandler),

            (r"/history", HistoryHandler),
            ]
        
        self.caat = options.caat

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
            database_namespace = 'mysql://%s' % database
            connection_url = 'mysql://%s:%s@localhost/%s?charset=utf8' % (
                admin_username, admin_password, database)
        else:
            database = "mango.db"
            database_namespace = 'sqlite:///%s' % database
            connection_url = 'sqlite:///%s' % database

        cache_namespace = sha1_concat(
            sys.version,
            sqlalchemy_version,
            database_namespace,
            )
    
        engine = create_engine(
            connection_url,
            #echo=True,
            )

        self.orm = scoped_session(sessionmaker(
                bind=engine,
                autocommit=False,
                query_cls=SafeQueryClass(),
                ))

        self.cache = MemcacheCache(cache_namespace)

        self.lookup = TemplateLookup(directories=['template'],
                                     input_encoding='utf-8',
                                     output_encoding='utf-8',
                                     default_filters=["unicode", "h"],
                                     )

        log_location = "log/arms_map.py.log"
        log_max_bytes = 1048576

        try:
            os.mkdir(os.path.dirname(log_location))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e
            

        logger = logging.getLogger()
        handler = logging.handlers.RotatingFileHandler(
            log_location, maxBytes=log_max_bytes)
        logging.getLogger().addHandler(handler)

        settings["xsrf_cookies"] = False
        
        tornado.web.Application.__init__(self, self.handler_list, **settings)

        print """CAAT Mapping Application running.
  Port: %d
  Cache namespace: %s""" % (options.port, cache_namespace)
        


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
