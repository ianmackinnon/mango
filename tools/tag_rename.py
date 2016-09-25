#!/usr/bin/env python
# -*- coding: utf-8 -*-

# pylint: disable=invalid-name
# Using `Tag` for tag class type

import sys

sys.path.append(".")

import logging

from optparse import OptionParser, OptionError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from model import connection_url_app
from model import Orgtag, Eventtag



LOG = logging.getLogger('tag_rename')

TYPE_LIST = {
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



def main():
    LOG.addHandler(logging.StreamHandler())

    usage = """%%prog TAGTYPE BEFORE AFTER

TAGTYPE:   %s
Bulk rename tag paths.
""" % (", ".join(TYPE_LIST.keys()))

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="count", default=0,
                      help="Print verbose information for debugging.")
    parser.add_option("-q", "--quiet", dest="quiet",
                      action="count", default=0,
                      help="Suppress warnings.")
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="Dry run.", default=None)

    (options, args) = parser.parse_args()
    args = [arg.decode(sys.getfilesystemencoding()) for arg in args]

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + options.verbose - options.quiet))]
    LOG.setLevel(level)

    if len(args) != 3:
        parser.print_usage()
        sys.exit(1)

    tag_type, before, after = args

    try:
        Tag = TYPE_LIST.get(tag_type)
    except IndexError:
        raise OptionError

    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    orm = Session()

    tag_rename(orm, Tag, before, after)

    if not options.dry_run:
        orm.commit()


if __name__ == "__main__":
    main()
