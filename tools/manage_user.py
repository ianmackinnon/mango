#!/usr/bin/env python3

import sys
import logging
import argparse

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from model import mysql, CONF_PATH
from model import Auth, User



LOG = logging.getLogger('manage_user')



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Set moderator status of user, creating user if they "
        "don't already exist.")
    parser.add_argument(
        "--verbose", "-v",
        dest="verbose",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        dest="quiet",
        action="count", default=0,
        help="Suppress warnings.")
    parser.add_argument(
        "-m", "--moderator",
        action="store", dest="moderator",
        help="0 or 1.", default=None)
    parser.add_argument(
        "-l", "--lock",
        action="store", dest="lock",
        help="0 or 1.", default=None)

    parser.add_argument(
        "name", metavar="NAME",
        help="User's full name.")
    parser.add_argument(
        "gmail", metavar="GMAIL",
        help="Gmail address.")

    args = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(log_level)

    if len(args) != 2:
        parser.print_usage()
        sys.exit(1)

    if args.moderator is not None:
        if args.moderator not in ["0", "1"]:
            raise Exception("moderator must be 0 or 1")
        args.moderator = bool(int(args.moderator))

    if args.lock is not None:
        if args.lock not in ["0", "1"]:
            raise Exception("lock must be 0 or 1")
        args.lock = bool(int(args.lock))

    connection_url = mysql.connection_url_app(CONF_PATH)
    engine = create_engine(connection_url,)
    session_factory = sessionmaker(bind=engine, autocommit=False)
    orm = session_factory()

    user_name, auth_name = args

    openid_url = "https://www.google.com/accounts/o8/id"

    auth = Auth.get(orm, openid_url, auth_name)
    user = User.get(orm, auth, user_name)
    print((args.lock))
    if args.moderator is not None:
        user.moderator = args.moderator
    if args.lock is not None:
        user.locked = args.lock
    orm.commit()



if __name__ == "__main__":
    main()
