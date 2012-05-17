#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import errno
import logging

from mako.template import Template
from mako.lookup import TemplateLookup

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from handle.base import BaseHandler, authenticated
from handle.auth import AuthLoginHandler, AuthLoginLocalHandler, AuthLoginGoogleHandler, AuthLogoutHandler
from handle.user import UserHandler, UserListHandler
from handle.home import HomeHandler
from handle.note import NoteHandler, NoteListHandler
from handle.address import AddressHandler, AddressListHandler
from handle.organisation import OrganisationHandler, OrganisationListHandler, OrganisationNoteListHandler, OrganisationAddressListHandler
from handle.organisation_tag import OrganisationTagHandler, OrganisationTagListHandler, OrganisationTagNoteListHandler



define("port", default=8802, help="Run on the given port", type=int)



class Application(tornado.web.Application):

    session_cookie_name = "s"

    def load_cookie_secret(self):
        try:
            self.cookie_secret = open(".xsrf", "r").read().strip()
        except IOError as e:
            sys.stderr.write(
                "Could not open XSRF key. Run 'make' to generate one.\n"
                )
            sys.exit(1)

    def path_is_authenticated(self, path):
        for key, value in self.handler_list:
            if re.match(key, path) and hasattr(value, "get"):
                if hasattr(value.get, "authenticated") and \
                        value.get.authenticated == True:
                    return True
        return False
                
        
    def __init__(self):

        self.load_cookie_secret()

        settings = dict(
            xsrf_cookies=True,
            cookie_secret=self.cookie_secret,
            login_url="/auth/login",
            )

        re_id = "([1-9][0-9]*)"
        re_e_id = "([1-9][0-9]*)(?:,([1-9][0-9]*))?"

        self.handler_list = [
            (r"/", HomeHandler),

            (r"/user", UserListHandler),
            (r"/user/%s" % re_id , UserHandler),

            (r"/note", NoteListHandler),
            (r"/note/%s" % re_e_id, NoteHandler),

            (r"/organisation", OrganisationListHandler),
            (r"/organisation/%s" % re_e_id, OrganisationHandler),
            (r"/organisation/%s/note" % re_e_id, OrganisationNoteListHandler),
            (r"/organisation/%s/address" % re_e_id, OrganisationAddressListHandler),

            (r"/address", AddressListHandler),
            (r"/address/%s" % re_e_id, AddressHandler),
#            (r"/address/%s/note" % re_e_id, AddressNoteListHandler),

            (r"/organisation-tag", OrganisationTagListHandler),
            (r"/organisation-tag/%s" % re_e_id, OrganisationTagHandler),
            (r"/organisation-tag/%s/note" % re_e_id, OrganisationTagNoteListHandler),

            (r"/auth/login", AuthLoginHandler),
            (r"/auth/login/google", AuthLoginGoogleHandler),
            (r"/auth/login/local", AuthLoginLocalHandler),
            (r"/auth/logout", AuthLogoutHandler),
            ]

        connection_url = 'sqlite:///mango.db'
    
        engine = create_engine(connection_url)

        self.orm = scoped_session(sessionmaker(bind=engine, autocommit=False))

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



def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
