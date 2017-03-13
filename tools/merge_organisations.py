#!/usr/bin/env python3

# pylint: disable=wrong-import-position
# Import from working directory.

import sys
import urllib.request
import urllib.parse
import urllib.error
import logging
from hashlib import md5
import argparse

import redis
import Levenshtein

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

sys.path.append(".")

from model import mysql, CONF_PATH, attach_search
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
        LOG.error("Found: %s", [v.org_id for v in org_list])
        sys.exit(1)

    for o, org in enumerate(org_list):
        print("%d %s (%d)" % (o, org.name, org.org_id))
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
        "-t", "--threshold",
        action="store", default=0.9,
        help="Match ratio threshold.")
    parser.add_argument(
        "-k", "--characters",
        action="store", type=int, default=2,
        help="Number of initial characters to assume the same.")
    parser.add_argument(
        "-a", "--alpha",
        action="store",
        help="Letter of the alphabet to start at.")
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Dry run.")

    parser.add_argument(
        "org_id", metavar="ORG_ID",
        nargs="*",
        help="Integer organisation IDs to merge. If none are supplied "
        "automatic merging with default thresholds will take place.")

    args = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]

    LOG.setLevel(log_level)
    LOG_MODEL.setLevel(log_level)

    connection_url = mysql.connection_url_app(CONF_PATH)
    engine = create_engine(connection_url)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False)
    orm = session_factory()

    # `model.py` requires search to be attached
    # for re-indexing orgs after merging.
    attach_search(engine, orm)

    if not args.org_id:
        merge_organisations(
            orm, args.threshold, args.characters, args.alpha)
    else:
        try:
            org_id_list = [int(arg) for arg in args.org_id]
        except ValueError:
            parser.print_usage()
            sys.exit(1)

        multi_merge(orm, org_id_list)

    if args.dry_run:
        LOG.warning("rolling back")
        orm.rollback()
    else:
        LOG.info("Committing.")
        orm.commit()



if __name__ == "__main__":
    main()
