#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")

import redis
import urllib
import logging
import Levenshtein

from optparse import OptionParser

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from hashlib import md5

from model import connection_url_app, attach_search
from model import User, Org, Note, Address, Orgtag



log = logging.getLogger('merge')



redis_server = redis.Redis("localhost")



def hash(name_a, name_b):
    return "caat-directory:%s" % md5(
        name_a.encode("utf-8") + "|||" + name_b.encode("utf-8")
        ).hexdigest()



def merge(orm, master, alias, moderation_user=None):
    print "MERGE: '%s' -> '%s'" % (alias.name, master.name)
    master.merge(alias, moderation_user)



def multi_merge(orm, org_id_list):
    user = orm.query(User).filter_by(user_id=-1).one()

    org_id_list = list(set(org_id_list))

    if len(org_id_list) <= 1:
        log.warning("Multiple orgs required.")
        sys.exit(1)

    org_list = orm.query(Org).filter(Org.org_id.in_(org_id_list)).all()

    if not len(org_list) == len(org_id_list):
        log.error("Could not find all IDs.")
        sys.exit(1)

    for o, org in enumerate(org_list):
        print o, org.name.encode("utf-8")
    print
    print "Choose merge target number or non-numeric to exit: ",

    choice = raw_input()

    try:
        choice = int(choice)
    except ValueError as e:
        log.warning("Could not convert %s to integer." % choice)
        sys.exit(1)

    if choice >= len(org_list) or choice < 0:
        log.error("%d is out of range." % choice)
        sys.exit(1)

    main = org_list.pop(choice)

    for org in org_list:
        main.merge(org, moderation_user=user)



def left_right_false(left, right):
    while True:
        print "'%s'\n'%s' | [L/R/F]?" % (left, right)
        print "https://www.google.es/search?q=%s" % urllib.quote_plus(right.encode("utf-8"))
        choice = raw_input().lower()
        if choice in 'lrf':
            return {'l':"L", "r":"R", "f":False}[choice]



def get(name_l, name_r):
    log.info("GET: %s %s" % (name_l, name_r))
    key = hash(name_l, name_r)
    try:
        value = redis_server.get(key)
        log.info("%s", value)
    except redis.ConnectionError as e:
        log.warning("Connection to redis server on localhost failed.")
        return None
    if value == "False":
        value = False
    log.info("%s" % value)
    return value



def put(name_l, name_r, value):
    log.info("PUT: %s %s %s" % (name_l, name_r, value))
    key = hash(name_l, name_r)
    try:
        redis_server.set(key, value)
    except redis.ConnectionError as e:
        log.warning("Connection to redis server on localhost failed.")



def main(orm, threshold, c, alpha=None):
    user = orm.query(User).filter_by(user_id=-1).one()

    similar = []

    org_list = orm.query(Org)
    if alpha:
        org_list = org_list.filter(func.lower(Org.name) >= alpha.lower())
    org_list = org_list.order_by(func.lower(Org.name)).all()

    for org_i in org_list:
        log.info(org_i.name)
        org_list_start = orm.query(Org).filter(func.lower(Org.name) >= org_i.name.lower())
        if c:
            org_list_start = org_list_start.filter(Org.name.like(org_i.name[:c] + "%"))
        org_list_start = org_list_start.all()
        
        for org_j in org_list_start:
            if org_i == org_j:
                continue
            ratio = Levenshtein.ratio(org_i.name.lower(), org_j.name.lower())
            if ratio > threshold:
                value = get(org_i.name, org_j.name)
                if value == False:
                    continue
                if value == "L":
                    merge(orm, org_i, org_j, user)
                    continue
                if value == "R":
                    merge(orm, org_j, org_i, user)
                    continue

                choice = left_right_false(org_i.name, org_j.name)
                if choice == "L":
                    merge(orm, org_i, org_j, user)
                    put(org_i.name, org_j.name, "L")
                    put(org_j.name, org_i.name, "R")
                    continue
                if choice == "R":
                    merge(orm, org_j, org_i, user)
                    put(org_j.name, org_i.name, "L")
                    put(org_i.name, org_j.name, "R")
                    continue
                put(org_i.name, org_j.name, False)
                put(org_j.name, org_i.name, False)



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%prog [ID]...

ID:   Integer organisation IDs to merge."""


    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)

    parser.add_option("-t", "--threshold", action="store", dest="threshold",
                      help="Match ratio threshold.", default=0.9)
    parser.add_option("-k", "--characters", action="store", dest="characters", type=int,
                      help="Number of initial characters to assume the same.", default=2)
    parser.add_option("-a", "--alpha", action="store", dest="alpha",
                      help="Letter of the alphabet to start at.", default=None)
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="Dry run.", default=None)

    (options, args) = parser.parse_args()

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))
    log.setLevel(
        (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[verbosity]
        )


    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    Session = sessionmaker(bind=engine, autocommit=False)
    orm = Session()
    attach_search(engine, orm)


    if len(args) == 0:
        main(orm, options.threshold, options.characters, options.alpha)
    else:
        try:
            org_id_list = [int(arg) for arg in args]
        except ValueError:
            parser.print_usage()
            sys.exit(1)

        multi_merge(orm, org_id_list)

    if options.dry_run:
        log.warning("rolling back")
        orm.rollback()
    else:
        log.info("Committing.")
        orm.commit()
    




