#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

sys.path.append(".")

import logging

from optparse import OptionParser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import mysql.mysql_init

from model import Auth, User, Session



log = logging.getLogger('insert_user')



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%prog NAME GMAIL"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)
    parser.add_option("-d", "--database", action="store", dest="database",
                      help="sqlite or mysql.", default="sqlite")
    parser.add_option("-c", "--configuration", action="store",
                      dest="configuration", help=".conf file.",
                      default=".mango.conf")

    (options, args) = parser.parse_args()

    if not len(args) == 2:
        parser.print_usage()
        sys.exit(1)

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))

    if options.database == "mysql":
        (database,
         app_username, app_password,
         admin_username, admin_password) = mysql.mysql_init.get_conf(
            options.configuration)
        connection_url = 'mysql://%s:%s@localhost/%s?charset=utf8' % (
            admin_username, admin_password, database)
    else:
        connection_url = 'sqlite:///mango.db'

    engine = create_engine(connection_url, echo=True)
    Session = sessionmaker(bind=engine, autocommit=False)
    orm = Session()

    user_name, auth_name = args

    openid_url = u"https://www.google.com/accounts/o8/id"

    auth = Auth(openid_url, auth_name)
    user = User(auth, user_name, moderator=True)

    orm.add(auth)
    orm.add(user)
    orm.commit()

