#!/usr/bin/env python3

import sys
import logging
import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model import mysql, CONF_PATH, attach_search
from model import User, Org, Orgtag, \
    VIRTUAL_ORGTAG_LIST, virtual_org_orgtag_all
from model import LOG as LOG_MODEL



LOG = logging.getLogger('set_virtual_tags')



def shell_red(text):
    return "\033[91m%s\033[0m" % text

def shell_blue(text):
    return "\033[94m%s\033[0m" % text



def create_all_virtual_orgtags(orm, system_user):
    for virtual_name, _filter_search in VIRTUAL_ORGTAG_LIST:
        LOG.info(virtual_name)

        virtual_tag = orm.query(Orgtag) \
            .filter_by(name=virtual_name) \
            .first()

        if not virtual_tag:
            LOG.info("creating")
            virtual_tag = Orgtag(virtual_name,
                                 moderation_user=system_user,
                                 public=False)
            virtual_tag.is_virtual = True
            orm.add(virtual_tag)
        else:
            if virtual_tag.is_virtual != True:
                raise Exception(
                    "Tag '%s' already exists but is not virtual." %
                    virtual_tag.name)

    orm.commit()



def check_orgtags(orm, org_id_list=None):
    query = orm.query(Org)
    if org_id_list:
        query = query.filter(Org.org_id.in_(org_id_list))

    total = query.count()
    for i, org in enumerate(query.all(), 1):
        if i % 100 == 0:
            LOG.info("%5d/%d", i, total)
        LOG.debug(shell_blue(org.name))

        if LOG.level == logging.DEBUG:
            before = [orgtag.orgtag_id for orgtag in org.orgtag_list]
        virtual_org_orgtag_all(org)
        if LOG.level == logging.DEBUG:
            if before != [orgtag.orgtag_id for orgtag in org.orgtag_list]:
                LOG.warning(shell_red("Changed: %s" % org.name))

    orm.commit()



def main():
    LOG.addHandler(logging.StreamHandler())
    LOG_MODEL.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Update virtual tags.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "--create", "-c",
        action="store_true",
        help="Create tags that don't already exist.")

    parser.add_argument(
        "org_id", metavar="ORG_ID",
        nargs="*",
        help="List of Org IDs to set, otherwise set all orgs. "
        "May not be used with `-c` option.")

    args = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + args.verbose - args.quiet))]

    LOG.setLevel(log_level)
    LOG_MODEL.setLevel(log_level)

    connection_url = mysql.connection_url_app(CONF_PATH)
    engine = create_engine(connection_url)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False)
    orm = session_factory()
    attach_search(engine, orm)

    try:
        org_id_list = [int(arg) for arg in args]
    except ValueError:
        LOG.error("Could not convert all arguments to integers.")
        parser.print_usage()
        sys.exit(1)

    if args.create:
        if org_id_list:
            parser.print_usage()
            sys.exit(1)
        system_user = orm.query(User).filter_by(user_id=-1).one()
        create_all_virtual_orgtags(orm, system_user)
        return

    check_orgtags(orm, org_id_list)



if __name__ == "__main__":
    main()
