#!/usr/bin/env python3

# pylint: disable=wrong-import-position,import-error
# Allow appending to import path before import
# Must also specify `PYTHONPATH` when invoking Pylint.

import os
import sys
import logging
import argparse
import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from model import connection_url_app, attach_search
from model import Medium, Auth, User, Session, Orgtag, Eventtag, \
    Org, Orgalias, Event, Address, Contact, Note



LOG = logging.getLogger('seed_data')



PATH = os.path.dirname(os.path.realpath(__file__))
MALICIOUS = os.path.join(PATH, "malicious.md")
with open(MALICIOUS, "r", encoding="utf-8") as f:
    MALICIOUS_MARKDOWN = f.read()



def user(auth, name, moderator=False, locked=False):
    u = User(auth, name, moderator, locked)
    Session(u, "0.0.0.0", "en", "moz")
    return u



def seed_data(orm):
    email = orm.query(Medium).filter_by(name="Email").one()

    auth_1 = Auth(
        "https://www.google.com/accounts/o8/id",
        "blah1@gmail.com"
        )
    user_1_mod = user(auth_1, "Moderator 1", moderator=True)
    auth_2 = Auth(
        "https://www.google.com/accounts/o8/id",
        "blah2@gmail.com"
        )
    user_2_lok = user(auth_2, "Locked 1", moderator=True, locked=True)
    user_3_non = user(None, "Non-moderator 1", moderator=False)
    public_1 = {
        "moderation_user": user_1_mod,
        "public": True,
        }

    orgtag_1 = Orgtag("Org Tag 1", **public_1)
    eventtag_1 = Eventtag("Event Tag 1", **public_1)

    orgtag_act_1 = Orgtag("Activity | Arms", **public_1)
    orgtag_exc_1 = Orgtag("Activity Exclusion | Fake Arms", **public_1)

    org_1 = Org("RÄndom Incorporated", MALICIOUS_MARKDOWN, **public_1)
    orm.add(org_1)
    org_1.orgtag_list.append(orgtag_1)
    _org_1_alias_1 = Orgalias("Randcorp", org_1, **public_1)
    org_1_address_1 = Address(
        "1 VictoriÀ Street, London, SW1H 0ET",
        "source",
        **public_1
        )
    org_1.address_list.append(org_1_address_1)
    org_1_contact_1 = Contact(
        email, "blah@example.com", "desc", "source", **public_1)
    org_1.contact_list.append(org_1_contact_1)
    org_1_note_1 = Note("Note about RI.", "source", **public_1)
    org_1.note_list.append(org_1_note_1)
    org_1_address_1_note_1 = Note(
        "Note about RI address.", "source", **public_1)
    org_1_address_1.note_list.append(org_1_address_1_note_1)

    event_1 = Event(
        "Event 1 Ü",
        datetime.date(2014, 12, 1),
        datetime.date(2014, 12, 1),
        "An event Ü",
        datetime.time(11, 44),
        datetime.time(13, 52),
        **public_1
        )
    orm.add(event_1)
    event_1.eventtag_list.append(eventtag_1)
    event_1_address_1 = Address(
        "1 VictoriÀ Street, London, SW1H 0ET",
        "source",
        **public_1
        )
    event_1.address_list.append(event_1_address_1)
    event_1_contact_1 = Contact(
        email, "blah@example.com", "desc", "source", **public_1)
    event_1.contact_list.append(event_1_contact_1)
    event_1_note_1 = Note("Event 1 NÖte 1.", "source", **public_1)
    event_1.note_list.append(event_1_note_1)

    org_1.event_list.append(event_1)

    orm.add_all((
        auth_1, user_1_mod, user_2_lok, user_3_non,
        orgtag_1, orgtag_act_1, orgtag_exc_1, eventtag_1,
        org_1, org_1_address_1, org_1_contact_1, org_1_note_1,
        event_1, event_1_address_1,
    ))
    print("OK")
    orm.commit()



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Seed database with example data for test suite.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)

    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    session_factory = sessionmaker(bind=engine, autocommit=False)
    orm = session_factory()
    attach_search(engine, orm)

    seed_data(orm)



if __name__ == "__main__":
    main()
