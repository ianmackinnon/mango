#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")

import time
import json
import codecs
import logging
import Levenshtein

from optparse import OptionParser

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

import geo
import mysql.mysql_init

from model import User, Org, Orgalias, Note, Address, Orgtag



log = logging.getLogger('insert_organisation')



def text_to_ngrams(text, size=5):
    ngrams = []
    for word in text.lower().split():
        length = len(word)
        space = u" " * (size - 1)
        word = space + word + space
        for i in xrange(length + size - 1):
            ngrams.append(word[i: i + size])
    return ngrams



def get_names(orm):
    names = {}
    for org in orm.query(Org).all():
        if not org.org_id in names:
            names[org.org_id] = []
        names[org.org_id].append(org.name)
    for orgalias in orm.query(Orgalias).all():
        org_id = orgalias.org.org_id
        if not org_id in names:
            names[org_id] = []
        names[org_id].append(orgalias.name)
    return names



def select_from_list(matches):
    for m, (name, alias) in enumerate(matches):
        print (u"  %4d  %s  %s" % (m, name, (alias and ("[%s]" % alias) or ""))).encode("utf-8")
    print
    print "Choose name or non-numeric to exit: ",

    choice = raw_input()

    try:
        choice = int(choice)
    except ValueError as e:
        log.warning("Could not convert %s to integer." % choice)
        return None

    if choice >= len(matches) or choice < 0:
        log.error("%d is out of range." % choice)
        return None

    return matches[choice][0]



def closest_names(name, names, orm):
    matches = set()

    lower = orm.query(Org.name).filter(Org.name > name).order_by(Org.name.asc()).limit(3).all()
    higher = orm.query(Org.name).filter(Org.name < name).order_by(Org.name.desc()).limit(3).all()

    for (name2, ) in lower + higher:
        matches.add((name2, None))

    for name2, alias in names:
        ratio = Levenshtein.ratio(name.lower(), name2.lower())
        if ratio > 0.8:
            matches.add((name2, alias))

    if not matches:
        return None

    matches = sorted(list(matches))

    print
    print         ("\n%s\n" % name).encode("utf-8")

    existing_name = select_from_list(matches)

    return existing_name

        

def get_org(orm, name):
    name = name.lower()

    query = orm.query(Org).filter(func.lower(Org.name)==name)
    try:
        return query.one()
    except NoResultFound:
        org = None
    except MultipleResultsFound:
        log.warning("Multiple results found for name '%s'." % name)
        return query.first()
        
    query = orm.query(Orgalias).filter(func.lower(Orgalias.name)==name)
    try:
        return query.one().org
    except NoResultFound:
        orgalias = None
    except MultipleResultsFound:
        log.warning("Multiple results found for alias '%s'." % name)
        return query.first().org

    return None



def search(names, search_text):
    org_id = None
    text = search_text

    while True:
        ngrams = {}

        sys.stderr.write((u"\nFind: '\033[92m%s\033[0m'\n\n" % (search_text)).encode("utf-8"))

        for org_id, name_list in names.items():
            length = len(name_list)
            for name in name_list:
                name_ngrams = text_to_ngrams(name)
                for key in name_ngrams:
                    if not key in ngrams:
                        ngrams[key] = {}
                    if not org_id in ngrams[key]:
                        ngrams[key][org_id] = 0
                    ngrams[key][org_id] += 1.0 / length

        for key in ngrams:
            total = sum([freq for org_id, freq in ngrams[key].items()])
            weight = 1.0 / total
            for org_id in ngrams[key]:
                ngrams[key][org_id] *= weight

        candidates = {}
        text_ngrams = text_to_ngrams(text)
        for key in text_ngrams:
            if not key in ngrams:
                continue
            for org_id, freq in ngrams[key].items():
                if not org_id in candidates:
                    candidates[org_id] = 0
                candidates[org_id] += freq

        candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)

        candidates_2 = [candidate for candidate in candidates if candidate[1] > 1]
        if candidates_2:
            candidates = candidates_2

        if not candidates_2:
            log.warning("        Low\n")
        for i, (org_id, freq) in enumerate(candidates[:10], 1):
            sys.stderr.write("  %4d: \033[37m%s %s\033[0m\n" % (i, org_id, freq))
            for name in names[org_id]:
                sys.stderr.write((u"        \033[94m%s\033[0m\n" % name).encode("utf-8"))
        sys.stderr.write("\n")
        sys.stderr.write(" Empty: None of the above\n")
        sys.stderr.write("  Text: Alternative search\n\n: ")
        choice = raw_input()
        if not len(choice):
            org_id = None
            break
        sys.stderr.write("\n")
        try:
            choice = int(choice)
        except ValueError:
            text = choice
            continue
        if choice == 0:
            org_id = "  "
            break
        if choice > len(candidates):
            continue
        org_id = candidates[choice - 1][0]
        break

    return org_id



def select_org(orm, name, user):
    org = get_org(orm, name)
    if org:
        return org

    names = get_names(orm)

    org_id = search(names, name)

    if not org_id:
        return None

    org = orm.query(Org).filter_by(org_id=org_id).one()

    orgalias = Orgalias(name, org, user, False)

    return org



def insert_fast(data, orm, public=None, tag_names=None, dry_run=None):
    user = orm.query(User).filter_by(user_id=-1).one()
    tag_names = tag_names or []
    names = None

    tags = []
    for tag_name in tag_names:
        tag = Orgtag.get(orm,
                         tag_name, 
                         moderation_user=user,
                         public=public,
                         )
        tags.append(tag)

    for chunk in data:
        log.info(("\n%s\n" % chunk["name"]).encode("utf-8"))
        org = select_org(orm, chunk["name"], user)

        if not org:
            log.warning((u"\nCreating org %s\n" % chunk["name"]).encode("utf-8"))
            org = Org(chunk["name"], moderation_user=user, public=public,)
            orm.add(org)

        if tags:
            org.orgtag_list = list(set(tags + org.orgtag_list))

        if "tag" in chunk:
            for tag_name in chunk["tag"]:
                tag = Orgtag.get(orm, tag_name, 
                                 moderation_user=user, public=True,
                                 )
                if tag not in org.orgtag_list:
                    org.orgtag_list.append(tag)
            

        if "address" in chunk:
            for address_data in chunk["address"]:
                if address_data["postal"] in \
                        [address.postal for address in org.address_list]:
                    continue
                address = Address(
                    address_data["postal"], address_data["source"],
                    moderation_user=user, public=None,
                    )
                address.geocode()
                log.debug(address)
                org.address_list.append(address)

        if "note" in chunk:
            for note_data in chunk["note"]:
                if note_data["text"] in [note.text for note in org.note_list]:
                    continue
                note = Note(
                    note_data["text"], note_data["source"],
                    moderation_user=user, public=None,
                    )
                log.debug(note)
                org.note_list.append(note)
        
        if not (orm.new or orm.dirty or orm.deleted):
            log.info("Nothing to commit.")
            continue

        if dry_run == True:
            log.warning("rolling back")
            orm.rollback()
            continue

        log.info("Committing.")
        orm.commit()



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%prog JSON..."""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)
    parser.add_option("-d", "--database", action="store", dest="database",
                      help="sqlite or mysql.", default="sqlite")
    parser.add_option("-c", "--configuration", action="store",
                      dest="configuration", help=".conf file.",
                      default=".mango.conf")
    parser.add_option("-t", "--tag", action="append", dest="tag",
                      help="Tag to apply to all insertions.", default=[])
    parser.add_option("-p", "--public", action="store",
                      dest="public", type=int,
                      help="Public state of new items (True, False, None).",
                      default=None)
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="Dry run.", default=None)

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_usage()
        sys.exit(1)

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))

    log.setLevel(
        (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[verbosity]
        )

    if options.database == "mysql":
        (database,
         app_username, app_password,
         admin_username, admin_password) = mysql.mysql_init.get_conf(
            options.configuration)
        connection_url = 'mysql://%s:%s@localhost/%s?charset=utf8' % (
            admin_username, admin_password, database)
    else:
        connection_url = 'sqlite:///mango.db'

    engine = create_engine(connection_url, echo=False)
    Session = sessionmaker(bind=engine, autocommit=False)
    orm = Session()

    if options.public != None:
        options.public = bool(options.public)

    for arg in args:
        try:
            data = json.load(codecs.open(arg, "r", "utf8"))
        except ValueError:
            log.error("%s: Could not decode JSON data.", arg)
            continue

        insert_fast(data, orm, options.public, options.tag, options.dry_run)

