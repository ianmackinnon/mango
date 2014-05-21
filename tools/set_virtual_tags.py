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
from model import log as log_model



log = logging.getLogger('set_virtual_tags')



def shell_red(text):
    return u"\033[91m%s\033[0m" % text

def shell_blue(text):
    return u"\033[94m%s\033[0m" % text



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



def check_orgtags(orm, org_id_list=None):
    query = orm.query(Org)
    if org_id_list:
        query = query.filter(Org.org_id.in_(org_id_list))

    total = query.count()
    for i, org in enumerate(query.all(), 1):
        if (i % 100 == 0):
            log.info(u"%5d/%d" % (i, total))
        log.debug(shell_blue(org.name))

        if log.level == logging.DEBUG:
            before = [orgtag.orgtag_id for orgtag in org.orgtag_list]
        virtual_org_orgtag_all(org)
        if log.level == logging.DEBUG:
            if before != [orgtag.orgtag_id for orgtag in org.orgtag_list]:
                log.warning(shell_red(u"Changed: %s" % org.name))

    orm.commit()



def main():
    log.addHandler(logging.StreamHandler())
    log_model.addHandler(logging.StreamHandler())

    usage = """%prog [ORG_ID...]

ORG_ID      List of Org IDs to set, otherwise set all orgs.
            May not be used with -c option.

"""


    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)
    parser.add_option("-c", "--create", action="store_true", dest="create",
                      help="Create tags that don't already exist.", default=None)

    (options, args) = parser.parse_args()
    args = [arg.decode(sys.getfilesystemencoding()) for arg in args]

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[max(0, min(3, 1 + options.verbose - options.quiet))]

    log.setLevel(log_level)
    log_model.setLevel(log_level)

    connection_url = connection_url_app()
    engine = create_engine(connection_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    orm = Session()
    attach_search(engine, orm)

    try:
        org_id_list = [int(arg) for arg in args]
    except ValueError as e:
        log.error("Could not convert all arguments to integers.")
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

