#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

sys.path.append(".")

import json
import codecs
import logging

from optparse import OptionParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

import geo
import mysql.mysql_init

from model import User, Org, Note, Address, Orgtag



log = logging.getLogger('insert_organisation')



def insert(data, tag_names):
    raise Exception("Use -f flag for fast insert")

    for chunk in data:
        org = get_or_make_organisation(chunk["name"])
        for address in chunk["address"]:
            org = organisation_add_address(org, address["postal"], address["source"])

        for note_data in chunk["note"]:
            note = make_note(note_data["text"], note_data["source"])
            print note
            organisation_add_note(org, note)
        
        org = update_organisation(org)



def insert_fast(data, orm, tag_names):
    user = orm.query(User).filter_by(user_id=-1).one()

    tags = []
    for tag_name in tag_names:
        tag = Orgtag.get(orm, tag_name, 
                         moderation_user=user, public=True,
                         )
        tags.append(tag)

    for chunk in data:
        log.info(chunk["name"])

        org = Org.get(
            orm, chunk["name"],
            accept_alias=True,
            moderation_user=user, public=None,
            )

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
    parser.add_option("-f", "--fast", action="store_true", dest="fast",
                      help="Fast insert at the DB level.", default=False)
    parser.add_option("-t", "--tag", action="append", dest="tag",
                      help="Tag to apply to all insertions.", default=[])

    (options, args) = parser.parse_args()

    if len(args) == 0:
        parser.print_usage()
        sys.exit(1)

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))

    log.setLevel(
        (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[verbosity]
        )

    if options.fast:
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

    for arg in args:
        try:
            data = json.load(codecs.open(arg, "r", "utf8"))
        except ValueError:
            log.error("%s: Could not decode JSON data.", arg)
            continue

        if options.fast:
            insert_fast(data, orm, options.tag)
        else:
            insert(data, options.tag)
        
