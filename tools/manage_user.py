#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

sys.path.append(".")

import logging

from optparse import OptionParser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from model import connection_url_admin
from model import Auth, User



LOG = logging.getLogger('manage_user')



def main():
    LOG.addHandler(logging.StreamHandler())

    usage = """%prog NAME GMAIL

Set moderator status of user, creating user if they don't already exist.
"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="count", default=0,
                      help="Print verbose information for debugging.")
    parser.add_option("-q", "--quiet", dest="quiet",
                      action="count", default=0,
                      help="Suppress warnings.")
    parser.add_option("-m", "--moderator", action="store", dest="moderator",
                      help="0 or 1.", default=None)
    parser.add_option("-l", "--lock", action="store", dest="lock",
                      help="0 or 1.", default=None)

    (options, args) = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + options.verbose - options.quiet))]
    LOG.setLevel(log_level)

    if len(args) != 2:
        parser.print_usage()
        sys.exit(1)

    if options.moderator is not None:
        if options.moderator not in ["0", "1"]:
            raise Exception("moderator must be 0 or 1")
        options.moderator = bool(int(options.moderator))

    if options.lock is not None:
        if options.lock not in ["0", "1"]:
            raise Exception("lock must be 0 or 1")
        options.lock = bool(int(options.lock))

    connection_url = connection_url_admin()
    engine = create_engine(connection_url,)
    session_factory = sessionmaker(bind=engine, autocommit=False)
    orm = session_factory()

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



if __name__ == "__main__":
    main()
