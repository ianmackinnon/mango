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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

import geo
import mysql.mysql_init

from model import User, Org, Orgalias, Note, Address, Orgtag



log = logging.getLogger('insert_organisation')



names = None



def get_names(orm):
    global names
    names = set()
    records = orm.query(Org.name).all()
    for record in records:
        names.add(record.name)
    records = orm.query(Orgalias.name).all()
    for record in records:
        names.add(record.name)



def select_from_list(matches):
    for m, match in enumerate(matches):
        print (u"  %4d  %s" % (m, match)).encode("utf-8")
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

    return matches[choice]



def closest_names(name, names, orm):
    matches = set()

    lower = orm.query(Org.name).filter(Org.name > name).order_by(Org.name.asc()).limit(3).all()
    higher = orm.query(Org.name).filter(Org.name < name).order_by(Org.name.desc()).limit(3).all()

    for (name2, ) in lower + higher:
        matches.add(name2)

    for name2 in names:
        ratio = Levenshtein.ratio(name.lower(), name2.lower())
        if ratio > 0.8:
            matches.add(name2)

    if not matches:
        return None

    matches = sorted(list(matches))

    print
    print         ("\n%s\n" % name).encode("utf-8")

    existing_name = select_from_list(matches)

    return existing_name

        

def get_org(orm, name):
    try:
        return orm.query(Org).filter_by(name=name).one()
    except NoResultFound:
        org = None
    except MultipleResultsFound:
        log.warning("Multiple results found for name '%s'." % name)
        return orm.query(Org).filter_by(name=name).first()
        
    try:
        orgalias = orm.query(Orgalias).filter_by(name=name).one()
    except NoResultFound:
        orgalias = None
    except MultipleResultsFound:
        log.warning("Multiple results found for alias '%s'." % name)
        orgalias = orm.query(Orgalias).filter_by(name=name).first()

    if orgalias:
        return orgalias.org

    return None



def select_org(orm, name, user):
    org = get_org(orm, name)
    if org:
        return org

    if names == None:
        get_names(orm)
    
    existing_name = closest_names(name, names, orm)

    if not existing_name:
        return None

    log.info((u"Chose name '%s'" % existing_name).encode("utf-8"))
    org = get_org(orm, existing_name)

    if not org:
        return None

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
            log.warning("Nothing to commit.")
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

