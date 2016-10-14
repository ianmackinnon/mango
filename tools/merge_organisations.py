#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import urllib.request
import urllib.parse
import urllib.error
import logging
from hashlib import md5
from optparse import OptionParser

import redis
import Levenshtein

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from model import connection_url_app, attach_search
from model import User, Org
from model import LOG as LOG_MODEL



LOG = logging.getLogger('merge')



REDIS_SERVER = redis.Redis("localhost")



def hash_digest(name_a, name_b):
    return "caat-directory:%s" % md5(
        name_a.encode("utf-8") + "|||" + name_b.encode("utf-8")
        ).hexdigest()



def merge(master, alias, moderation_user=None):
    print("MERGE: '%s' -> '%s'" % (alias.name, master.name))
    master.merge(alias, moderation_user)



def multi_merge(orm, org_id_list):
    user = orm.query(User).filter_by(user_id=-1).one()

    org_id_list = list(set(org_id_list))

    if len(org_id_list) <= 1:
        LOG.warning("Multiple orgs required.")
        sys.exit(1)

    org_list = orm.query(Org).filter(Org.org_id.in_(org_id_list)).all()

    if len(org_list) != len(org_id_list):
        LOG.error("Could not find all IDs.")
        sys.exit(1)

    for o, org in enumerate(org_list):
        print("%d %s (%d)" % (o, org.name.encode("utf-8"), org.org_id))
    print()
    print("Choose merge target number or non-numeric to exit: ", end=' ')

    choice = input()

    try:
        choice = int(choice)
    except ValueError:
        LOG.warning("Could not convert %s to integer.", choice)
        sys.exit(1)

    if choice >= len(org_list) or choice < 0:
        LOG.error("%d is out of range.", choice)
        sys.exit(1)

    master = org_list.pop(choice)

    engine = orm.connection().engine
    for org in org_list:
        master.merge(org, moderation_user=user)

        sql = "update org_address_v set org_id = %d where org_id = %d" % (
            master.org_id, org.org_id)
        engine.execute(sql)

        sql = "update org_contact_v set org_id = %d where org_id = %d" % (
            master.org_id, org.org_id)
        engine.execute(sql)




def left_right_false(left, right):
    while True:
        print("'%s'\n'%s' | [L/R/F]?" % (left, right))
        print("https://www.google.es/search?q=%s" % urllib.parse.quote_plus(right.encode("utf-8")))
        choice = input().lower()
        if choice in 'lrf':
            return {'l':"L", "r":"R", "f":False}[choice]



def get(name_l, name_r):
    LOG.info("GET: %s %s", name_l, name_r)
    key = hash_digest(name_l, name_r)
    try:
        value = REDIS_SERVER.get(key)
        LOG.info("%s", value)
    except redis.ConnectionError:
        LOG.warning("Connection to redis server on localhost failed.")
        return None
    if value == "False":
        value = False
    LOG.info("%s", value)
    return value



def put(name_l, name_r, value):
    LOG.info("PUT: %s %s %s", name_l, name_r, value)
    key = hash_digest(name_l, name_r)
    try:
        REDIS_SERVER.set(key, value)
    except redis.ConnectionError:
        LOG.warning("Connection to redis server on localhost failed.")



def merge_organisations(orm, threshold, c, alpha=None):
    user = orm.query(User).filter_by(user_id=-1).one()

    org_list = orm.query(Org)
    if alpha:
        org_list = org_list \
            .filter(func.lower(Org.name) >= alpha.lower())
    org_list = org_list.order_by(func.lower(Org.name)).all()

    for org_i in org_list:
        LOG.info(org_i.name)
        org_list_start = orm.query(Org) \
            .filter(func.lower(Org.name) >= org_i.name.lower())
        if c:
            org_list_start = org_list_start \
                .filter(Org.name.like(org_i.name[:c] + "%"))
        org_list_start = org_list_start.all()

        for org_j in org_list_start:
            if org_i == org_j:
                continue
            ratio = Levenshtein.ratio(org_i.name.lower(), org_j.name.lower())
            if ratio > threshold:
                value = get(org_i.name, org_j.name)
                if value is False:
                    continue
                if value == "L":
                    merge(org_i, org_j, user)
                    continue
                if value == "R":
                    merge(org_j, org_i, user)
                    continue

                choice = left_right_false(org_i.name, org_j.name)
                if choice == "L":
                    merge(org_i, org_j, user)
                    put(org_i.name, org_j.name, "L")
                    put(org_j.name, org_i.name, "R")
                    continue
                if choice == "R":
                    merge(org_j, org_i, user)
                    put(org_j.name, org_i.name, "L")
                    put(org_i.name, org_j.name, "R")
                    continue
                put(org_i.name, org_j.name, False)
                put(org_j.name, org_i.name, False)



def main():
    LOG.addHandler(logging.StreamHandler())
    LOG_MODEL.addHandler(logging.StreamHandler())

    usage = """%prog [ID]...

ID:   Integer organisation IDs to merge."""


    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="count", default=0,
                      help="Print verbose information for debugging.")
    parser.add_option("-q", "--quiet", dest="quiet",
                      action="count", default=0,
                      help="Suppress warnings.")
    parser.add_option("-t", "--threshold", action="store", dest="threshold",
                      help="Match ratio threshold.", default=0.9)
    parser.add_option("-k", "--characters", dest="characters",
                      action="store", type=int, default=2,
                      help="Number of initial characters to assume the same.")
    parser.add_option("-a", "--alpha", action="store", dest="alpha",
                      help="Letter of the alphabet to start at.", default=None)
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="Dry run.", default=None)

    (options, args) = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + options.verbose - options.quiet))]

    LOG.setLevel(log_level)
    LOG_MODEL.setLevel(log_level)

    connection_url = connection_url_app()
    engine = create_engine(connection_url)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False)
    orm = session_factory()
    attach_search(engine, orm)


    if len(args) == 0:
        merge_organisations(
            orm, options.threshold, options.characters, options.alpha)
    else:
        try:
            org_id_list = [int(arg) for arg in args]
        except ValueError:
            parser.print_usage()
            sys.exit(1)

        multi_merge(orm, org_id_list)

    if options.dry_run:
        LOG.warning("rolling back")
        orm.rollback()
    else:
        LOG.info("Committing.")
        orm.commit()



if __name__ == "__main__":
    main()
