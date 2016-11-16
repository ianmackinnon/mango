#!/usr/bin/env python3

import sys
import logging
import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from model import connection_url_app, attach_search
from model import User, Event, Eventtag, Org, Orgtag, Orgalias, Note, Address
from model_v import Org_v, Orgalias_v, Orgtag_v, Event_v, Eventtag_v, \
    Address_v, Note_v



LOG = logging.getLogger('restore')



TRANSACTION_TIME_THRESHOLD = 2



def get_existing_entity(orm, Entity, key, value):
    # pylint: disable=invalid-name
    # Allow `Entity` abstract class name.
    entity_query = orm.query(Entity) \
        .filter_by(**{key: value})
    return entity_query.first()



def get_deleted_entity(orm, Entity, Entity_v, key, value, key_v, d_time=None):
    # pylint: disable=invalid-name
    # Allow `Entity_v` and `Entity` abstract class names.
    entity = get_existing_entity(orm, Entity, key, value)
    if entity:
        return entity, None, None

    entity_v_deleted_query = orm.query(Entity_v) \
        .filter_by(**{key: value, "existence": False})
    if d_time is not None:
        entity_v_deleted_query = entity_v_deleted_query \
            .filter(Entity_v.a_time <= d_time + TRANSACTION_TIME_THRESHOLD) \
            .filter(Entity_v.a_time >= d_time - TRANSACTION_TIME_THRESHOLD)
    entity_v_deleted_query = entity_v_deleted_query \
        .order_by(Entity_v.a_time.desc())
    entity_v_deleted = entity_v_deleted_query.first()
    if not entity_v_deleted:
        LOG.debug("Deleted row not found.")
        return None, None, None

    entity_v_last = orm.query(Entity_v) \
        .filter_by(**{key: value}) \
        .filter(Entity_v.a_time <= entity_v_deleted.a_time) \
        .filter(getattr(Entity_v, key_v) != getattr(entity_v_deleted, key_v)) \
        .order_by(Entity_v.a_time.desc()) \
        .first()

    if not entity_v_last:
        LOG.warning("Existing row not found.")
        return None, None, None

    if not entity_v_last.existence:
        LOG.warning("Existing row not last.")
        return None, None, None

    return None, entity_v_last, entity_v_deleted.a_time



def get_deleted_entity_list(
        orm, Entity, Entity_v, key, value, key_2, key_v, d_time):
    # pylint: disable=invalid-name
    # Allow `Entity_v` and `Entity` abstract class names.
    entity_query = orm.query(Entity) \
        .filter_by(**{key: value})
    entity_list = entity_query.all()

    # Get all the deleted entities

    entity_v_deleted_query = orm.query(Entity_v) \
        .filter_by(**{key: value, "existence": False})
    if d_time is not None:
        entity_v_deleted_query = entity_v_deleted_query \
            .filter(Entity_v.a_time <= d_time + TRANSACTION_TIME_THRESHOLD) \
            .filter(Entity_v.a_time >= d_time - TRANSACTION_TIME_THRESHOLD)
    entity_v_deleted_list = entity_v_deleted_query \
        .order_by(Entity_v.a_time.desc()) \
        .all()

    # Get an existing version for each deleted entity

    entity_v_last_list = []

    for entity_v_deleted in entity_v_deleted_list:
        entity_v_last = orm.query(Entity_v) \
            .filter_by(**{
                key: value,
                key_2: getattr(entity_v_deleted, key_2),
                }) \
            .filter(
                Entity_v.a_time <= entity_v_deleted.a_time,
                getattr(Entity_v, key_v) != getattr(entity_v_deleted, key_v)
            ) \
            .order_by(Entity_v.a_time.desc()) \
            .first()
        if not entity_v_last:
            LOG.warning("Existing row not found (list %s %s).", )
            continue
        if not entity_v_last.existence:
            LOG.warning("Existing row not last.")
            continue
        entity_v_last_list.append(entity_v_last)

    return entity_list, entity_v_last_list



def get_deleted_child_id_list(
        orm, table_name, table_name_v, key, value, key_2, d_time):
    engine = orm.connection().engine

    deleted_id_list = []

    # Get existing links

    sql = """
select %s from %s
where %s = %d""" % (
    key_2, table_name,
    key, value,
)
    results = engine.execute(sql)

    for (value_2, ) in results:
        if value_2 in deleted_id_list:
            continue
        LOG.warning("Found existing cross link for %s:%d", key_2, value_2)
        deleted_id_list.append(value_2)

    # Get deleted links

    sql = """
select %s, a_time from %s
where %s = %d
and existence = 0""" % (
    key_2, table_name_v,
    key, value,
)
    if d_time is not None:
        sql += """
and a_time <= %.3f
and a_time >= %.3f""" % (
    d_time + TRANSACTION_TIME_THRESHOLD,
    d_time - TRANSACTION_TIME_THRESHOLD,
)
    sql += """
order by a_time desc"""
    results = engine.execute(sql)

    # Get last existing version of deleted links

    for value_2, a_time in results:
        if value_2 in deleted_id_list:
            continue
        sql = """
select existence from %s
where %s = %d
and %s = %d
and a_time <= %.3f
and existence = 1
order by a_time desc
limit 1""" % (
    table_name_v,
    key, value,
    key_2, value_2,
    a_time,
)
        result = list(engine.execute(sql))
        if not result:
            LOG.warning(
                "Existing row not found (id %s %s %s).", key_2, value_2, sql)
            sys.exit(1)
            continue
        if not result[0]:
            LOG.warning("Existing row not last.")
            continue
        deleted_id_list.append(value_2)

    return deleted_id_list



def restore_note(orm, user, note_id, historic, d_time=None):
    LOG.info("Restoring note %d", note_id)

    d_time = historic and d_time or None
    note, note_v, d_time = get_deleted_entity(
        orm, Note, Note_v, "note_id", note_id, "note_v_id", d_time)
    d_time = historic and d_time or None

    if note:
        LOG.warning("Note %d already exists.", note_id)
        return note

    if not note_v:
        LOG.error(
            "Cannot restore note %d because no recently "
            "deleted versions exist.",
            note_id)
        return None

    LOG.info("deleted time: %s", d_time)

    note = Note(
        note_v.text, note_v.source,
        user, note_v.public)
    note.note_id = note_v.note_id
    orm.add(note)

    return note



def restore_orgtag(orm, _user, orgtag_id):
    LOG.info("Restoring orgtag %d", orgtag_id)


    orgtag, _orgtag_v, _d_time = get_deleted_entity(
        orm, Orgtag, Orgtag_v, "orgtag_id", orgtag_id, "orgtag_v_id", None)

    if orgtag:
        LOG.warning("Orgtag %d already exists.", orgtag_id)
        return orgtag

    raise NotImplementedError



def restore_eventtag(orm, _user, eventtag_id):
    LOG.info("Restoring eventtag %d", eventtag_id)


    eventtag, _eventtag_v, _d_time = get_deleted_entity(
        orm, Eventtag, Eventtag_v,
        "eventtag_id", eventtag_id, "eventtag_v_id", None)

    if eventtag:
        LOG.warning("Eventtag %d already exists.", eventtag_id)
        return eventtag

    raise NotImplementedError



def restore_address(orm, user, address_id, historic, d_time=None):
    LOG.info("Restoring address %d", address_id)

    d_time = historic and d_time or None
    address, address_v, d_time = get_deleted_entity(
        orm, Address, Address_v,
        "address_id", address_id, "address_v_id", d_time)
    d_time = historic and d_time or None

    if address:
        LOG.warning("Address %d already exists.", address_id)
        return address

    if not address_v:
        LOG.error(
            "Cannot restore address %d because no recently "
            "deleted versions exist.",
            address_id)
        return None

    LOG.info("deleted time: %s", d_time)

    address = Address(
        address_v.postal, address_v.source, address_v.lookup,
        address_v.manual_longitude, address_v.manual_latitude,
        address_v.longitude, address_v.latitude,
        user, address_v.public)
    address.address_id = address_v.address_id
    del address_v
    orm.add(address)

    note_id_list = get_deleted_child_id_list(
        orm, "address_note", "address_note_v",
        "address_id", address_id, "note_id", d_time)

    for note_id in note_id_list:
        note = restore_note(orm, user, note_id, historic, d_time)
        if not note:
            continue
        if note in address.note_list:
            LOG.warning(
                "Not linking note %s, already linked to this address.",
                note_id)
            continue
        address.note_list.append(note)

    return address



def restore_org(orm, user, org_id, historic, d_time=None):
    LOG.info("Restoring org %d", org_id)

    d_time = historic and d_time or None
    org, org_v, d_time = get_deleted_entity(
        orm, Org, Org_v, "org_id", org_id, "org_v_id", d_time)
    d_time = historic and d_time or None

    if org:
        LOG.warning("Org %d already exists.", org_id)
        return org

    if not org_v:
        LOG.error(
            "Cannot restore org %d because no recently "
            "deleted versions exist.",
            org_id)
        return None

    LOG.info("deleted time: %s", d_time)

    org = Org(org_v.name,
              description=org_v.description,
              moderation_user=user,
              public=org_v.public)
    org.org_id = org_v.org_id
    del org_v
    orm.add(org)


    _orgalias_list, orgalias_v_list = get_deleted_entity_list(
        orm, Orgalias, Orgalias_v,
        "org_id", org_id, "orgalias_id", "orgalias_v_id", d_time)

    for orgalias_v in orgalias_v_list:
        orgalias = Orgalias(orgalias_v.name, org, user, orgalias_v.public)
        orgalias.orgalias_id = orgalias_v.orgalias_id


    orgtag_id_list = get_deleted_child_id_list(
        orm, "org_orgtag", "org_orgtag_v",
        "org_id", org_id, "orgtag_id", d_time)

    for orgtag_id in orgtag_id_list:
        orgtag = restore_orgtag(orm, user, orgtag_id)
        if orgtag in org.orgtag_list:
            if not orgtag:
                continue
            LOG.warning(
                "Not linking orgtag %s, already linked to this org.",
                orgtag_id)
            continue
        org.orgtag_list.append(orgtag)


    address_id_list = get_deleted_child_id_list(
        orm, "org_address", "org_address_v",
        "org_id", org_id, "address_id", d_time)

    for address_id in address_id_list:
        address = restore_address(orm, user, address_id, historic, d_time)
        if not address:
            continue
        if address.org_list or address.event_list:
            LOG.warning(
                "Not linking address %s, already linked to another entity.",
                address_id)
            continue
        if address in org.address_list:
            LOG.warning(
                "Not linking address %s, already linked to this org.",
                address_id)
            continue
        org.address_list.append(address)


    note_id_list = get_deleted_child_id_list(
        orm, "org_note", "org_note_v", "org_id", org_id, "note_id", d_time)

    for note_id in note_id_list:
        note = restore_note(orm, user, note_id, historic, d_time)
        if not note:
            continue
        if note in org.note_list:
            LOG.warning(
                "Not linking note %s, already linked to this org.", note_id)
            continue
        org.note_list.append(note)


    event_id_list = get_deleted_child_id_list(
        orm, "org_event", "org_event_v", "org_id", org_id, "event_id", d_time)

    for event_id in event_id_list:
        event = get_existing_entity(orm, Event, "event_id", event_id)
        if event:
            if event in org.event_list:
                LOG.warning(
                    "Not linking event %s, already linked to this org.",
                    event_id)
                continue
            org.event_list.append(event)
        else:
            LOG.warning("Not restoring link to deleted event %d.", event_id)


    return org



def restore_event(orm, user, event_id, historic, d_time=None):
    LOG.info("Restoring event %d", event_id)

    d_time = historic and d_time or None
    event, event_v, d_time = get_deleted_entity(
        orm, Event, Event_v, "event_id", event_id, "event_v_id", d_time)
    d_time = historic and d_time or None

    if event:
        LOG.warning("Event %d already exists.", event_id)
        return event

    if not event_v:
        LOG.error(
            "Cannot restore event %d because no recently "
            "deleted versions exist.",
            event_id)
        return None

    LOG.info("deleted time: %s", d_time)

    event = Event(
        event_v.name, event_v.start_date, event_v.end_date,
        event_v.description, event_v.start_time, event_v.end_time,
        user, event_v.public)
    event.event_id = event_v.event_id
    del event_v
    orm.add(event)


    eventtag_id_list = get_deleted_child_id_list(
        orm, "event_eventtag", "event_eventtag_v",
        "event_id", event_id, "eventtag_id", d_time)

    for eventtag_id in eventtag_id_list:
        eventtag = restore_eventtag(orm, user, eventtag_id)
        if not eventtag:
            continue
        if eventtag in event.eventtag_list:
            LOG.warning(
                "Not linking eventtag %s, already linked to this event.",
                eventtag_id)
            continue
        event.eventtag_list.append(eventtag)


    address_id_list = get_deleted_child_id_list(
        orm, "event_address", "event_address_v",
        "event_id", event_id, "address_id", d_time)

    for address_id in address_id_list:
        address = restore_address(orm, user, address_id, historic, d_time)
        if not address:
            continue
        if address.org_list or address.event_list:
            LOG.warning(
                "Not linking address %s, already linked to another entity.",
                address_id)
            continue
        if address in event.address_list:
            LOG.warning(
                "Not linking address %s, already linked to this event.",
                address_id)
            continue
        event.address_list.append(address)


    note_id_list = get_deleted_child_id_list(
        orm, "event_note", "event_note_v",
        "event_id", event_id, "note_id", d_time)

    for note_id in note_id_list:
        note = restore_note(orm, user, note_id, historic, d_time)
        if not note:
            continue
        if note in event.note_list:
            LOG.warning(
                "Not linking note %s, already linked to this event.",
                note_id)
            continue
        event.note_list.append(note)


    org_id_list = get_deleted_child_id_list(
        orm, "org_event", "org_event_v", "event_id", event_id, "org_id", d_time)

    for org_id in org_id_list:
        org = get_existing_entity(orm, Org, "org_id", org_id)
        if org:
            if org in event.org_list:
                LOG.warning(
                    "Not linking org %s, already linked to this event.",
                    org_id)
                continue
            event.org_list.append(org)
        else:
            LOG.warning("Not restoring link to deleted org %d.", org_id)


    return event


def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Restore an organisation or event.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Dry run.")
    parser.add_argument(
        "--ignore-timestamp", "-i",
        action="store_false",
        help="Ignore timestamp.", default=True)
    parser.add_argument(
        "--organisation", "-O",
        action="store", type="int",
        help="Restore organisation by ID.")
    parser.add_argument(
        "--event", "-E",
        action="store", type="int",
        help="Restore event by ID.")

    args = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + args.verbose - args.quiet))]

    LOG.setLevel(log_level)

    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    session_factory = sessionmaker(bind=engine, autocommit=False)
    orm = session_factory()
    attach_search(engine, orm)

    user = orm.query(User).filter_by(user_id=-1).one()

    if args.org:
        org = restore_org(orm, user, args.organisation, args.ignore_timestamp)
        if org:
            LOG.info(org.pprint())

    if args.event:
        event = restore_event(orm, user, args.event, args.ignore_timestamp)
        if event:
            LOG.info(event.pprint())

    if args.dry_run:
        LOG.warning("rolling back")
        orm.rollback()
    else:
        LOG.info("Committing.")
        orm.commit()



if __name__ == "__main__":
    main()
