#!/usr/bin/env python3

# pylint: disable=wrong-import-position
# Adding working directory to system path

import sys
import logging
import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(".")

from mysql import mysql
from model import CONF_PATH, attach_search
from model import Orgtag, org_orgtag



LOG = logging.getLogger('tag_unlink')



def confirm(text, default=True):
    choice = None
    options = "Y/n" if default else "y/N"
    while True:
        sys.stdout.write("\n  %s [%s]" % (text, options))
        sys.stdout.flush()

        choice = input().strip().lower()

        if choice == "":
            return default

        if choice in ("y", "yes"):
            return True
        if choice in ("n", "no"):
            return False

        sys.stderr.write("  Please enter “y” or “n”.\n")
        sys.stderr.flush()



def tag_unlink(orm, name, force=None, dry_run=None):

    orgtag_list = orm.query(Orgtag) \
        .filter(Orgtag.name_short.like(name)) \
        .all()

    org_orgtag_count = orm.query(org_orgtag) \
        .join(Orgtag) \
        .filter(Orgtag.name_short.like(name)) \
        .count()

    LOG.info("\nFound %d org tags with %d links to orgs.\n",
             len(orgtag_list), org_orgtag_count)

    for orgtag in orgtag_list:
        count = orm.query(org_orgtag) \
            .filter(org_orgtag.c.orgtag_id == orgtag.orgtag_id) \
            .count()
        LOG.info("  %4d : %s" % (count, orgtag.name))
    LOG.info("")

    if not org_orgtag_count:
        LOG.warning("Nothing to do.")
        sys.exit(0)

    if not force:
        if not confirm("Delete %d orgtag links?" % org_orgtag_count):
            sys.exit(1)

    sql = """
    delete org_orgtag
    from org_orgtag
    inner join orgtag on org_orgtag.orgtag_id = orgtag.orgtag_id
    where orgtag.name_short like "{name}";
    """.format(**{
        "name": name
    })

    orm.execute(sql)

    if dry_run is True:
        LOG.warning("Dry run: rolling back")
        orm.rollback()
        return

    LOG.info("Deleted %d links to orgtags matching %s:" % (
        org_orgtag_count, name))
    orm.commit()



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Fully unlink organisation tags.")

    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force. Do not ask whether to delete.")
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Dry run.")

    parser.add_argument(
        "tag_name", metavar="TAG",
        nargs="+",
        help="Name of organisation tag to fully unlink. "
        "`%` may be used as a wildcard.")

    args = parser.parse_args()

    # Default log level is INFO (2)
    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 2 + args.verbose - args.quiet))]
    LOG.setLevel(log_level)

    connection_url = mysql.connection_url_app(CONF_PATH)
    engine = create_engine(connection_url,)
    mysql.engine_disable_mode(engine, "ONLY_FULL_GROUP_BY")
    session_ = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    orm = session_()
    attach_search(engine, orm)

    for name in args.tag_name:
        tag_unlink(orm, name, force=args.force, dry_run=args.dry_run)



if __name__ == "__main__":
    main()
