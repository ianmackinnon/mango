#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

sys.path.append(".")

import logging

from optparse import OptionParser
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import mysql.mysql_init

from model import Orgtag, Eventtag



log = logging.getLogger('tag_rename')

type_list = {
    "org": Orgtag,
    "event": Eventtag,
    }



def tag_rename(orm, Tag, before, after):
    print before
    print after

    tag_list = orm.query(Tag) \
        .filter(Tag.name.startswith(before)) \
        .all()

    for tag in tag_list:
        tag.name = tag.name.replace(before, after, 1)
        print tag.name

    print len(tag_list)



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%%prog TAGTYPE BEFORE AFTER

TAGTYPE:   %s
Bulk rename tag paths.
""" % (", ".join(type_list.keys()))

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
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="Dry run.", default=None)

    (options, args) = parser.parse_args()
    args = [arg.decode(sys.getfilesystemencoding()) for arg in args]

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))

    if not len(args) == 3:
        parser.print_usage()
        sys.exit(1)

    tag_type, before, after = args
    
    try:
        Tag = type_list.get(tag_type)
    except IndexError as e:
        raise OptionError

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

    tag_rename(orm, Tag, before, after)

    if not options.dry_run:
        orm.commit()

