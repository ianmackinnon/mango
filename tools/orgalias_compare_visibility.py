#!/usr/bin/env python3
# pylint: disable=wrong-import-position
# Adding working directory to system path

import sys
import logging
import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(".")

from model import mysql, CONF_PATH, attach_search
from model import Org, Orgalias, calculate_orgalias_visibility



LOG = logging.getLogger('insert_organisation')
LOG_MODEL = logging.getLogger('model')
LOG_SEARCH = logging.getLogger('search')



def compare_visibility(orm, dry_run=None, reset=None):
    # pylint: disable=singleton-comparison
    # Cannot use `is` in SQLAlchemy filters

    if reset:
        orm.query(Orgalias).update({
            "public": None
        })
    if not dry_run:
        orm.commit()

    org_query = orm.query(Org) \
        .filter(
            Org.public == True,
        )

    total = org_query.count()

    for i, org in enumerate(org_query):
        if i % 100 == 0:
            LOG.info("%d/%d, %0.0f%% complete", i, total, i * 100 / total)
        LOG.debug("Org: %s", org.name)
        calculate_orgalias_visibility(org)

    if not dry_run:
        LOG.info("Committing.")
        orm.commit()



def main():
    LOG.addHandler(logging.StreamHandler())
    LOG_MODEL.addHandler(logging.StreamHandler())
    LOG_SEARCH.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(description="__DESC__")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "-r", "--reset",
        action="store_true",
        help="Reset all aliases to null visibility before starting.")

    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Dry run.")


    args = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(log_level)
    LOG_MODEL.setLevel(log_level)
    LOG_SEARCH.setLevel(log_level)

    connection_url = mysql.connection_url_app(CONF_PATH)
    engine = create_engine(connection_url,)
    session_ = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    orm = session_()
    attach_search(engine, orm)

    compare_visibility(
        orm,
        dry_run=args.dry_run, reset=args.reset
    )



if __name__ == "__main__":
    main()
