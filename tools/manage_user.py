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



log = logging.getLogger('manage_user')



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%prog NAME GMAIL

Set moderator status of user, creating user if they don't already exist.
"""

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
    parser.add_option("-m", "--moderator", action="store", dest="moderator",
                      help="0 or 1.", default=None)
    parser.add_option("-l", "--lock", action="store", dest="lock",
                      help="0 or 1.", default=None)

    (options, args) = parser.parse_args()

    if not len(args) == 2:
        parser.print_usage()
        sys.exit(1)

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))

    if options.moderator is not None:
        if options.moderator not in ["0", "1"]:
            raise Exception("moderator must be 0 or 1")
        options.moderator = bool(int(options.moderator))

    if options.lock is not None:
        if options.lock not in ["0", "1"]:
            raise Exception("lock must be 0 or 1")
        options.lock = bool(int(options.lock))

    if options.database == "mysql":
        (database,
         app_username, app_password,
         admin_username, admin_password) = mysql.mysql_init.get_conf(
            options.configuration)
        connection_url = 'mysql://%s:%s@localhost/%s?charset=utf8' % (
            admin_username, admin_password, database)
    else:
        connection_url = 'sqlite:///mango.db'

    engine = create_engine(connection_url)
    Session = sessionmaker(bind=engine, autocommit=False)
    orm = Session()

    user_name, auth_name = args

    openid_url = u"https://www.google.com/accounts/o8/id"

    auth = Auth.get(orm, openid_url, auth_name)
    user = User.get(orm, auth, user_name)
    print options.lock
    if options.moderator is not None:
        user.moderator = options.moderator
    if options.lock is not None:
        user.locked = options.lock
    orm.commit()

