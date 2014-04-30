#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")

import time
import datetime
import json
import codecs
import logging

from optparse import OptionParser

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

import geo

from model import connection_url_app, attach_search
from model import Medium, Auth, User, Orgtag, Eventtag, Org, Orgalias, Event, Address, Contact, Note



log = logging.getLogger('seed_data')


lorem_markdown = u"ÜunicÖde. Lorem ipsum dolor sit amet\n\nconsectetur adipisicing elit, sed do eiusmod tempor\n\nincididunt ut labore et dolore magna aliqua."



def main(orm):
    email = orm.query(Medium).filter_by(name=u"Email").one()

    auth_1 = Auth(
        u"https://www.google.com/accounts/o8/id",
        u"blah1@gmail.com"
        )
    user_1_mod = User(auth_1, u"Moderator 1", moderator=True)
    auth_2 = Auth(
        u"https://www.google.com/accounts/o8/id",
        u"blah2@gmail.com"
        )
    user_2_lok = User(auth_2, u"Locked 1", moderator=True, locked=True)
    user_3_non = User(None, u"Non-moderator 1", moderator=False)
    public_1 = {
        "moderation_user": user_1_mod,
        "public": True,
        }

    orgtag_1 = Orgtag(u"Org Tag 1", **public_1)
    eventtag_1 = Eventtag(u"Event Tag 1", **public_1)

    org_1 = Org(u"RÄndom Incorporated", lorem_markdown, **public_1)
    orm.add(org_1)
    org_1.orgtag_list.append(orgtag_1)
    org_1_alias_1 = Orgalias(u"Randcorp", org_1, **public_1)
    org_1_address_1 = Address(
        u"1 VictoriÀ Street, London, SW1H 0ET",
        u"source",
        **public_1
        )
    org_1.address_list.append(org_1_address_1)
    org_1_contact_1 = Contact(email, u"blah@example.com", u"desc", u"source", **public_1)
    org_1.contact_list.append(org_1_contact_1)
    org_1_note_1 = Note(u"Note about RI.", u"source", **public_1)
    org_1.note_list.append(org_1_note_1)
    org_1_address_1_note_1 = Note(u"Note about RI address.", u"source", **public_1)
    org_1_address_1.note_list.append(org_1_address_1_note_1)

    event_1 = Event(
        u"Event 1 Ü",
        datetime.date(2014, 12, 1),
        datetime.date(2014, 12, 1),
        u"An event Ü",
        datetime.time(11, 44),
        datetime.time(13, 52),
        **public_1
        )
    orm.add(event_1)
    event_1.eventtag_list.append(eventtag_1)
    event_1_address_1 = Address(
        u"1 VictoriÀ Street, London, SW1H 0ET",
        u"source",
        **public_1
        )
    event_1.address_list.append(event_1_address_1)
    event_1_contact_1 = Contact(email, u"blah@example.com", u"desc", u"source", **public_1)
    event_1.contact_list.append(event_1_contact_1)
    event_1_note_1 = Note(u"Event 1 NÖte 1.", u"source", **public_1)
    event_1.note_list.append(event_1_note_1)

    orm.add_all((
            auth_1, user_1_mod, user_2_lok, user_3_non,
            orgtag_1, eventtag_1,
            org_1, org_1_address_1, org_1_contact_1, org_1_note_1,
            event_1, event_1_address_1,
            ))
    print "OK"
    orm.commit()



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%prog JSON..."""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)

    (options, args) = parser.parse_args()

    if len(args):
        parser.print_usage()
        sys.exit(1)

    verbosity = max(0, min(3, 1 + options.verbose - options.quiet))

    log.setLevel(
        (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[verbosity]
        )


    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    Session = sessionmaker(bind=engine, autocommit=False)
    orm = Session()
    attach_search(engine, orm)

    main(orm)
