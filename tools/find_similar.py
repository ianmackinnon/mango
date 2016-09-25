#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")

import os
import codecs
import inspect
import logging

from optparse import OptionParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model import connection_url_app, attach_search
from model import User, Org



LOG = logging.getLogger('find_similar')

SETTING_PATH = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
CSV_PATH = os.path.join(SETTING_PATH, "similar.csv")
CSV_PATH_TMP = os.path.join("/tmp", "similar.csv")



def org_key(a, b):
    return tuple(sorted([a, b]))



def read_csv(path):
    data = {}
    try:
        with codecs.open(path, "r", "utf-8") as csv_file:
            for line in csv_file.readlines():
                line = line.strip()
                if not line:
                    pass
                match, org_id_a, org_id_b = line.split(", ")
                match = bool(int(match))
                org_id_a = int(org_id_a)
                org_id_b = int(org_id_b)
                key = org_key(org_id_a, org_id_b)
                data[key] = match
    except IOError:
        pass
    return data



def write_csv(path, data):
    with codecs.open(path, "w", "utf-8") as csv_file:
        for key in sorted(data.keys()):
            org_id_a, org_id_b = key
            match = int(data[key])
            csv_file.write(u"%d, %d, %d\n" % (match, org_id_a, org_id_b))
    print "written", path



def nearest(es, name, org_id, blacklist):
    data = {
        "size": len(blacklist) + 1,
        "query": {
            "filtered": {
                "query": {
                    "multi_match": {
                        "fields": [
                            "alias.straight^3",
                            "alias.fuzzy",
                            ],
                        "query": name
                        }
                    },
                "filter": {
                    "numeric_range" : {
                        "org_id" : {
                            "from" : org_id,
                            "include_lower" : False
                            }
                        }
                    }
                }
            }
        }
    results = es.search(data, index="mango", doc_type="org")
    if not results:
        return
    results = results["hits"]["hits"]
    if blacklist:
        print "BLACKLIST", org_id, blacklist
    for result in results:
        if result["_source"]["org_id"] not in blacklist:
            return result



def ignore(similar, org_id):
    blacklist = set()
    for a, b in similar.keys():
        if a == org_id:
            blacklist.add(b)
        if b == org_id:
            blacklist.add(a)
    return blacklist



def find_similar(orm, similar):
    user = orm.query(User).filter_by(user_id=-1).one()
    es = orm.get_bind().search

    hit_list = []
    max_length = 30
    i = 0
    interval = 30

#    while True:
#        org = orm.query(Org).order_by(func.rand()).first()

    for o, org in enumerate(orm.query(Org).all()):
        if not org:
            break

        blacklist = ignore(similar, org.org_id)

        hit = nearest(es, org.name, org.org_id, blacklist)
        if not hit:
            continue

        if len(hit_list) < max_length or hit["_score"] > hit_list[-1]["_score"]:
            hit["_orig"] = org
            hit_list.append(hit)
            hit_list.sort(key=lambda h: h["_score"], reverse=True)
            hit_list = hit_list[:max_length]


        i += 1
        if i == interval:
            i = 0
            print
            print o
            hit = hit_list.pop(0)

            key = org_key(hit["_orig"].org_id, hit["_source"]["org_id"])
            if key in similar:
                print "SIM", key, similar[key]
                continue
            print (u" %40s  %40s " % (hit["_orig"].org_id,
                                      hit["_source"]["org_id"])).encode("utf-8")
            print (" %40s  %40s " % (hit["_orig"].public,
                                     hit["_source"]["public"])).encode("utf-8")
            print (" %40s  %40s " % (hit["_orig"].name,
                                     hit["_source"]["name"])).encode("utf-8")
            for alias in hit["_source"]["alias"][1:]:
                print " %40s  %40s " % ("", alias)
            print
            print "Merge? (%.2f)" % hit["_score"]
            print
            print "Enter = do not merge"
            print "[l] = left is main"
            print "[r] = right is main"
            print "[ u] = pUblic"
            print "[ e] = pEnding"
            print "[ i] = prIvate"
            print ">",
            value = raw_input()
            if value and value[0] in "lr":
                org_b = orm.query(Org) \
                    .filter(Org.org_id == hit["_source"]["org_id"]) \
                    .one()
                public = "DEFAULT"
                if len(value) > 1 and value[1] in "uei":
                    public = {"u": True, "e": None, "i": False}[value[1]]
                if value[0] == "l":
                    hit["_orig"].merge(org_b, user)
                    if public != "DEFAULT":
                        hit["_orig"].public = public
                else:
                    org_b.merge(hit["_orig"], user)
                    if public != "DEFAULT":
                        org_b.public = public
                orm.commit()
                key = org_key(hit["_orig"].org_id, hit["_source"]["org_id"])
                similar[key] = True
                write_csv(CSV_PATH, similar)
            else:
                key = org_key(hit["_orig"].org_id, hit["_source"]["org_id"])
                similar[key] = False
                write_csv(CSV_PATH, similar)




def main():
    LOG.addHandler(logging.StreamHandler())

    usage = """%prog"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="count", default=0,
                      help="Print verbose information for debugging.")
    parser.add_option("-q", "--quiet", dest="quiet",
                      action="count", default=0,
                      help="Suppress warnings.")

    (options, args) = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + options.verbose - options.quiet))]
    LOG.setLevel(level)

    if args:
        parser.print_usage()
        sys.exit(1)

    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    session_ = sessionmaker(bind=engine, autocommit=False)
    orm = session_()
    attach_search(engine, orm)

    similar = read_csv(CSV_PATH)

    find_similar(orm, similar)


if __name__ == "__main__":
    main()
