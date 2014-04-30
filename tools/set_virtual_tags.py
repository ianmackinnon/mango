#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")

import logging

from optparse import OptionParser

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from model import connection_url_app, attach_search
from model import User, Org, Orgtag, virtual_orgtag_list, virtual_org_orgtag_all



log = logging.getLogger('set_virtual_tags')



def create_all_virtual_orgtags(orm, system_user):
    for virtual_name, filter_search in virtual_orgtag_list:
        log.info(virtual_name)

        virtual_tag = orm.query(Orgtag) \
            .filter_by(name=virtual_name) \
            .first()

        if not virtual_tag:
            log.info("creating")
            virtual_tag = Orgtag(virtual_name,
                                 moderation_user=system_user,
                                 public=False)
            virtual_tag.virtual = True
            orm.add(virtual_tag)
        else:
            if virtual_tag.virtual != True:
                raise Exception("Tag '%s' already exists but is not virtual." % virtual_tag.name)

    orm.commit()



def check_orgtags(orm):
    total = orm.query(Org).count()
    for i, org in enumerate(orm.query(Org).all(), 1):
        print "%d/%d  %s" % (i, total, org.name)
        virtual_org_orgtag_all(org)
    orm.commit()



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%prog"""


    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)
    parser.add_option("-c", "--create", action="store_true", dest="create",
                      help="Create tags that don't already exist.", default=None)

    (options, args) = parser.parse_args()

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))
    log.setLevel(
        (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[verbosity]
        )

    connection_url = connection_url_app()
    engine = create_engine(connection_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    orm = Session()
    attach_search(engine, orm)

    if args:
        parser.print_usage()
        sys.exit(1)

    if options.create:
        system_user = orm.query(User).filter_by(user_id=-1).one()
        create_all_virtual_orgtags(orm, system_user)
    else:
        check_orgtags(orm)




