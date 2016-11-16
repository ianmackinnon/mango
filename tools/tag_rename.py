#!/usr/bin/env python3

# pylint: disable=invalid-name
# Using `Tag` for tag class type

import sys
import logging
import argparse
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
    print(before)
    print(after)

    tag_list = orm.query(Tag) \
        .filter(Tag.name.startswith(before)) \
        .all()

    for tag in tag_list:
        tag.name = tag.name.replace(before, after, 1)
        print((tag.name))

    print((len(tag_list)))



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Bulk rename tag paths.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Dry run.")

    parser.add_argument(
        "tag_type", metavar="TAGTYPE",
        help="Tag type. Options: %s." % ", ".join(TYPE_LIST))
    parser.add_argument(
        "before", metavar="BEFORE",
        help="Tag name before.")
    parser.add_argument(
        "after", metavar="AFTER",
        help="Tag name after.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)

    try:
        Tag = TYPE_LIST.get(args.tag_type)
    except IndexError:
        LOG.error("Tag type must be one of %s", ", ".join(TYPE_LIST))
        sys.exit(1)

    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    orm = Session()

    tag_rename(orm, Tag, args.before, args.after)

    if not args.dry_run:
        orm.commit()


if __name__ == "__main__":
    main()
