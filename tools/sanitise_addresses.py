#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")
import logging
import re

from optparse import OptionParser

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

import mysql.mysql_init

from model import User, Org, Note, Address, Orgtag



log = logging.getLogger('sanitize_addresses')



def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":True,   "y":True,  "ye":True,
             "no":False,     "n":False}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")


re_code = re.compile("([^\W\d]\d|\d[^\W\d])", re.UNICODE)

def split_postcode(line):
    def is_code(text):
        return bool(re_code.search(text))

    ret = [[]]
    last_code = None
    for part in line.split():
        this_code = is_code(part)
        if len(ret[0]) and this_code != last_code:
            ret.append([])
        ret[-1].append(part)
        last_code = this_code
    for p, part in enumerate(ret):
        ret[p] = " ".join(part)
    return ret

def suspicious_postcodes(orm):

    print "Suspicious postcodes"
    print

    for address in orm.query(Address):
        parts = Address.parts(address.postal)
        for part in parts[len(parts)/2:]:
            if re_code.search(part):
                split = split_postcode(part)
                if len(split) > 1:
                    print
                    print address.url
                    print repr(part)
                    print split





def sanitise_addresses(orm):
    user = orm.query(User).filter_by(user_id=-1).one()

    for address in orm.query(Address):
        a = address.postal
        b = address.sanitise_address(address.postal)
        if (a != b):
            if "," not in b:
                address.postal = b
                print b.encode("utf-8")
                print
                orm.commit()
                continue
            b = address.sanitise_address(address.postal, False)
            print
            print a.encode("utf-8")
            print
            print b.encode("utf-8")
            print
            if query_yes_no(u"replace?", default=None):
                address.postal = b
                orm.commit()




if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%prog [ID]...

ID:   Integer organisation IDs to merge."""


    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)
    parser.add_option("-c", "--configuration", action="store",
                      dest="configuration", help=".conf file.",
                      default=".mango.conf")
    parser.add_option("-d", "--database", action="store", dest="database",
                      help="sqlite or mysql.", default="sqlite")

    (options, args) = parser.parse_args()

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))
    log.setLevel(
        (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[verbosity]
        )

    if options.database == "mysql":
        (database,
         app_username, app_password,
         admin_username, admin_password) = mysql.mysql_init.get_conf(
            options.configuration)
        connection_url = 'mysql://%s:%s@localhost/%s?charset=utf8' % (
            admin_username, admin_password, database)
    else:
        connection_url = 'sqlite:///mango.db'

    engine = create_engine(connection_url, echo=False)
    Session = sessionmaker(bind=engine, autocommit=False)
    orm = Session()

#    sanitise_addresses(orm);

    suspicious_postcodes(orm);
