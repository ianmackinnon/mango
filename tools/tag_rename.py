#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

sys.path.append(".")

import logging

from optparse import OptionParser, OptionError
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from model import connection_url_app
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

    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    orm = Session()

    tag_rename(orm, Tag, before, after)

    if not options.dry_run:
        orm.commit()

