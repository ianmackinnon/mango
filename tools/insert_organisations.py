#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append(".")

import json
import codecs
import logging
from optparse import OptionParser

import Levenshtein

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from model import connection_url_app, attach_search, sanitise_name
from model import User, Org, Orgalias, Note, Address, Orgtag, Contact, Medium



LOG = logging.getLogger('insert_organisation')
LOG_SEARCH = logging.getLogger('search')



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
        if org.org_id not in names:
            names[org.org_id] = []
        names[org.org_id].append(org.name)
    for orgalias in orm.query(Orgalias).all():
        org_id = orgalias.org.org_id
        if org_id not in names:
            names[org_id] = []
        names[org_id].append(orgalias.name)
    return names



def select_from_list(matches):
    for m, (name, alias) in enumerate(matches):
        print (
            u"  %4d  %s  %s" % (m, name, (alias and ("[%s]" % alias) or ""))
        ).encode("utf-8")
    print
    print "Choose name or non-numeric to exit: ",

    choice = raw_input()

    try:
        choice = int(choice)
    except ValueError:
        LOG.warning("Could not convert %s to integer.", choice)
        return None

    if choice >= len(matches) or choice < 0:
        LOG.error("%d is out of range.", choice)
        return None

    return matches[choice][0]



def closest_names(name, names, orm):
    matches = set()

    lower = orm.query(Org.name) \
        .filter(Org.name > name) \
        .order_by(Org.name.asc()) \
        .limit(3) \
        .all()
    higher = orm.query(Org.name) \
        .filter(Org.name < name) \
        .order_by(Org.name.desc()) \
        .limit(3) \
        .all()

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

    query = orm.query(Org) \
        .filter(func.lower(Org.name) == name)

    try:
        return query.one()
    except NoResultFound:
        org = None
    except MultipleResultsFound:
        LOG.warning("Multiple results found for name '%s'." % name)
        return query.first()

    query = orm.query(Orgalias) \
        .filter(func.lower(Orgalias.name) == name)

    try:
        return query.one().org
    except NoResultFound:
        orgalias = None
    except MultipleResultsFound:
        LOG.warning("Multiple results found for alias '%s'." % name)
        return query.first().org

    return None



def get_candidates(es, text):
    data = {
        "query": {
            "multi_match": {
                "fields": [
                    "alias.straight^3",
                    "alias.fuzzy",
                    ],
                "query": text
                }
            }
        }
    results = es.search(data, index="mango", doc_type="org")
    org_list = []
    for hit in results["hits"]["hits"]:
        source = hit["_source"]
        source["score"] = hit["_score"]
        org_list.append(source)
    return org_list


def search_org(es, text_orig, just_search=False):
    """Returns False to skip"""

    org_id = None
    text_search = text_orig

    while True:
        candidates = get_candidates(es, text_search)
        if not candidates:
            break

        sys.stderr.write(
            (u"\nFind: '\033[92m%s\033[0m'\n\n" % (text_orig)).encode("utf-8")
        )
        for i, org in enumerate(candidates, 1):
            sys.stderr.write(
                "  %4d: \033[37m%-5d %s\033[0m\n" % (
                    i, org["org_id"], org["score"])
            )
            for name in org["alias"]:
                sys.stderr.write(
                    (u"        \033[94m%s\033[0m\n" % name).encode("utf-8")
                )
        sys.stderr.write("\n")
        sys.stderr.write(" Empty: None of the above\n")
        sys.stderr.write("  Text: Alternative search\n: ")
        sys.stderr.write("   '-': Skip\n\n: ")
        if just_search:
            return

        choice = raw_input()
        choice = choice.strip()
        if not len(choice):
            org_id = None
            break
        sys.stderr.write("\n")
        if choice == "-":
            org_id = False
            break
        sys.stderr.write("\n")
        try:
            choice = int(choice)
        except ValueError:
            text_search = choice
            continue
        if choice == 0:
            org_id = "  "
            break
        if choice > len(candidates):
            continue
        org_id = candidates[choice - 1]["org_id"]
        break

    return org_id



def select_org(orm, name, user, search=True):
    """Returns False to skip"""

    name = sanitise_name(name)

    org = get_org(orm, name)
    if org:
        return org

    if not search:
        return

    es = orm.get_bind().search
    if es is None:
        LOG.error("Cannot connect to Elasticsearch.")
        sys.exit(1)
    org_id = search_org(es, name)

    if not org_id:
        return org_id

    try:
        org = orm.query(Org).filter_by(org_id=org_id).one()
    except NoResultFound as e:
        LOG.warning("No result found for '%s', org_id '%d'.", name, org_id)
        raise e

    orgalias = Orgalias(name, org, user, False)

    return org



def insert_fast(
        data, orm,
        public=None, tag_names=None, dry_run=None, address_exclusive=None,
        search=True, org_id_whitelist=None
):
    user = orm.query(User).filter_by(user_id=-1).one()
    tag_names = tag_names or []

    tags = []
    for tag_name in tag_names:
        tag = Orgtag.get(
            orm,
            tag_name,
            moderation_user=user,
            public=public,
        )
        tags.append(tag)

    for chunk in data:
        # pylint: disable=maybe-no-member
        has_address = None
        LOG.info(("\n%s\n" % chunk["name"]).encode("utf-8"))
        org = select_org(orm, chunk["name"], user, search)

        if (
                org is False or
                (org_id_whitelist and
                 ((not org) or (org.org_id not in org_id_whitelist)))
        ):
            LOG.info("Skipping org: %s", org and org.org_id)
            orm.rollback()
            continue

        if not org:
            LOG.warning(
                (u"\nCreating org %s\n" % chunk["name"]).encode("utf-8"))
            org = Org(chunk["name"], moderation_user=user, public=public,)
            orm.add(org)
            # Querying org address list on a new org would trigger a commit
            has_address = False
        else:
            has_address = bool(org.address_list)

        if tags:
            org.orgtag_list = list(set(tags + org.orgtag_list))

        if "tag" in chunk:
            for tag_name in chunk["tag"]:
                tag = Orgtag.get(
                    orm, tag_name,
                    moderation_user=user, public=public,
                )
                if tag not in org.orgtag_list:
                    org.orgtag_list.append(tag)

        if "address" in chunk and not (address_exclusive and has_address):
            for address_data in chunk["address"]:
                if address_data["postal"] in \
                        [address.postal for address in org.address_list]:
                    continue
                address = Address(
                    address_data["postal"], address_data["source"],
                    moderation_user=user, public=None,
                    )
                address.geocode()
                LOG.debug(address)
                orm.add(address)
                org.address_list.append(address)

        if "contact" in chunk:
            for contact_data in chunk["contact"]:
                text = sanitise_name(contact_data["text"])
                match = False
                for contact in org.contact_list:
                    if (
                            contact.text == text and
                            contact.medium.name == contact_data["medium"]
                    ):
                        match = True
                        break
                if match:
                    continue

                try:
                    medium = orm.query(Medium) \
                        .filter_by(name=contact_data["medium"]) \
                        .one()
                except NoResultFound:
                    LOG.warning("%s: No such medium", contact_data["medium"])
                    continue

                contact = Contact(
                    medium, text,
                    source=contact_data["source"],
                    moderation_user=user, public=None,
                )
                LOG.debug(contact)
                orm.add(contact)
                org.contact_list.append(contact)

        if "note" in chunk:
            for note_data in chunk["note"]:
                if note_data["text"] in [note.text for note in org.note_list]:
                    continue
                note = Note(
                    note_data["text"], note_data["source"],
                    moderation_user=user, public=None,
                    )
                LOG.debug(note)
                orm.add(note)
                org.note_list.append(note)

        if not (orm.new or orm.dirty or orm.deleted):
            LOG.info("Nothing to commit.")
            continue

        if dry_run is True:
            LOG.warning("rolling back")
            orm.rollback()
            continue

        LOG.info("Committing.")
        orm.commit()



def main():
    LOG.addHandler(logging.StreamHandler())
    LOG_SEARCH.addHandler(logging.StreamHandler())

    usage = """%prog JSON..."""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", dest="verbose",
                      action="count", default=0,
                      help="Print verbose information for debugging.")
    parser.add_option("-q", "--quiet", dest="quiet",
                      action="count", default=0,
                      help="Suppress warnings.")

    parser.add_option("-t", "--tag", action="append", dest="tag",
                      help="Tag to apply to all insertions.", default=[])
    parser.add_option("-p", "--public", action="store",
                      dest="public", type=int,
                      help="Public state of new items (True, False, None).",
                      default=None)
    parser.add_option("-s", "--search", action="store_true",
                      dest="search",
                      help="Search string using import merge tool.",
                      default=None)
    parser.add_option("-d", "--do-not-search", action="store_true",
                      dest="no_search",
                      help="Do not search for similar org names.",
                      default=None)
    parser.add_option("-A", "--address-exclusive", action="store_true",
                      dest="address_exclusive",
                      help="Only import addresses if org has no existing "
                      "address.",
                      default=None)
    parser.add_option("-L", "--limit-org", action="store",
                      dest="limit_org",
                      help="Only apply changes to orgs whose IDs are "
                      "supplied (a comma separated string)",
                      default=None)
    parser.add_option("-n", "--dry-run", action="store_true", dest="dry_run",
                      help="Dry run.", default=None)

    (options, args) = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + options.verbose - options.quiet))]
    LOG.setLevel(level)
    LOG_SEARCH.setLevel(level)

    if len(args) == 0:
        parser.print_usage()
        sys.exit(1)

    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    session_ = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    orm = session_()
    attach_search(engine, orm)


    if options.public != None:
        options.public = bool(options.public)

    if options.search:
        es = orm.get_bind().search
        for arg in args:
            search_org(es, arg, just_search=True)
        sys.exit(0)

    org_id_whitelist = None
    if options.limit_org:
        org_id_whitelist = []
        for id_ in options.limit_org.split(","):
            org_id_whitelist.append(int(id_))

    for arg in args:
        try:
            data = json.load(codecs.open(arg, "r", "utf8"))
        except ValueError:
            LOG.error("%s: Could not decode JSON data.", arg)
            continue

        insert_fast(
            data, orm, options.public, options.tag, options.dry_run,
            options.address_exclusive, (not options.no_search),
            org_id_whitelist
        )



if __name__ == "__main__":
    main()
