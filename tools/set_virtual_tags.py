#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")

import logging

from optparse import OptionParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model import connection_url_app, attach_search
from model import User, Org, Orgtag, VIRTUAL_ORGTAG_LIST, virtual_org_orgtag_all
from model import LOG as LOG_MODEL



LOG = logging.getLogger('set_virtual_tags')



def shell_red(text):
    return u"\033[91m%s\033[0m" % text

def shell_blue(text):
    return u"\033[94m%s\033[0m" % text



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
                raise Exception("Tag '%s' already exists but is not virtual." % virtual_tag.name)

    orm.commit()



def check_orgtags(orm, org_id_list=None):
    query = orm.query(Org)
    if org_id_list:
        query = query.filter(Org.org_id.in_(org_id_list))

    total = query.count()
    for i, org in enumerate(query.all(), 1):
        if i % 100 == 0:
            LOG.info(u"%5d/%d", i, total)
        LOG.debug(shell_blue(org.name))

        if LOG.level == logging.DEBUG:
            before = [orgtag.orgtag_id for orgtag in org.orgtag_list]
        virtual_org_orgtag_all(org)
        if LOG.level == logging.DEBUG:
            if before != [orgtag.orgtag_id for orgtag in org.orgtag_list]:
                LOG.warning(shell_red(u"Changed: %s" % org.name))

    orm.commit()



def main():
    LOG.addHandler(logging.StreamHandler())
    LOG_MODEL.addHandler(logging.StreamHandler())

    usage = """%prog [ORG_ID...]

ORG_ID      List of Org IDs to set, otherwise set all orgs.
            May not be used with -c option.

"""

    parser = OptionParser(usage=usage)
    parser.add_option(
        "-v", "--verbose", dest="verbose",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_option(
        "-q", "--quiet", dest="quiet",
        action="count", default=0,
        help="Suppress warnings.")
    parser.add_option("-c", "--create", action="store_true", dest="create",
                      help="Create tags that don't already exist.", default=None)

    (options, args) = parser.parse_args()
    args = [arg.decode(sys.getfilesystemencoding()) for arg in args]

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + options.verbose - options.quiet))]

    LOG.setLevel(log_level)
    LOG_MODEL.setLevel(log_level)

    connection_url = connection_url_app()
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

    if options.create:
        if org_id_list:
            parser.print_usage()
            sys.exit(1)
        system_user = orm.query(User).filter_by(user_id=-1).one()
        create_all_virtual_orgtags(orm, system_user)
        return

    check_orgtags(orm, org_id_list)



if __name__ == "__main__":
    main()
