#!/usr/bin/env python3

# pylint: disable=invalid-name
# Allow `Entity`, `Entity_v` abstract class names

import sys
import logging
import argparse

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from model import connection_url_app
from model import Event, Eventtag, Org, Orgtag, Orgalias, Note, Address
from model_v import Org_v, Orgalias_v, Orgtag_v, Event_v, Eventtag_v, \
    Address_v, Note_v



LOG = logging.getLogger('audit')



D_TIME = 1358163906



def max_id(orm, Entity, Entity_v, key):
    m = None
    value = orm.query(func.max(getattr(Entity, key))).first()
    if value:
        m = max(m or 0, value[0])
    value = orm.query(func.max(getattr(Entity_v, key))).first()
    if value:
        m = max(m or 0, value[0])
    return m



def version(Entity_v, entity, key, value):
    entity_v = Entity_v()
    entity_v.existence = 1
    setattr(entity_v, key, value)
    entity_v.moderation_user_id = entity.moderation_user_id
    entity_v.a_time = entity.a_time
    entity_v.public = entity.public
    return entity_v



def compare_version(entity_v, entity, ignore_a_time=False):
    if entity_v.moderation_user_id != entity.moderation_user_id:
        LOG.warning("moderation_user_id")
        return 1
    if entity_v.public != entity.public:
        LOG.warning("public")
        return 1
    if ignore_a_time:
        return 0
    if entity_v.a_time != entity.a_time:
        LOG.warning("a_time")
        return 1
    return 0



def add_orgalias_version(orm, orgalias):
    orgalias_v = version(
        Orgalias_v, orgalias, "orgalias_id", orgalias.orgalias_id)
    orgalias_v.org_id = orgalias.org_id
    orgalias_v.name = orgalias.name
    orm.add(orgalias_v)
    return orgalias_v



def compare_orgalias(orgalias_v, orgalias, ignore_a_time=False):
    if compare_version(orgalias_v, orgalias, ignore_a_time):
        return 1
    if orgalias_v.org_id != orgalias.org_id:
        LOG.warning("org_id")
        return 1
    if orgalias_v.name != orgalias.name:
        LOG.warning("name")
        return 1
    return 0



def add(orm, Entity_v, entity, key, attr_list):
    entity_v = version(Entity_v, entity, key, getattr(entity, key))
    for attr in attr_list:
        setattr(entity_v, attr, getattr(entity, attr))
    orm.add(entity_v)
    return entity_v



def compare(entity_v, entity, attr_list, ignore_a_time=False):
    if compare_version(entity_v, entity, ignore_a_time):
        return 1
    for attr in attr_list:
        if getattr(entity_v, attr) != getattr(entity, attr):
            LOG.warning(attr)
            return 1
    return 0



def audit_entity(orm, Entity, Entity_v, key, key_v, attr):
    max_entity_id = max_id(orm, Entity, Entity_v, key)

    LOG.info(max_entity_id)

    for entity_id in range(0, max_entity_id + 1):
        if entity_id % 500 == 0:
            LOG.info(entity_id)
        entity = orm.query(Entity).filter_by(**{key: entity_id}).first()
        entity_v_list = orm.query(Entity_v) \
            .filter_by(**{key: entity_id}) \
            .order_by(getattr(Entity_v, key_v).desc()) \
            .all()
        entity_v = entity_v_list and entity_v_list[0] or None

        if not entity_id:
            if entity:
                LOG.warning("key %d: Exists.", entity_id)
                continue
            if entity_v:
                LOG.warning("key %d: Versions exist.", entity_id)
                continue
            continue

        if entity:
            if not entity_v:
                LOG.warning("key %d: Exists with no versions.", entity_id)
                print((add(orm, Entity_v, entity, key, attr)))
                continue

            if not entity_v.existence:
                LOG.warning(
                    "key %d: Exists but last version is deleted.", entity_id)
                print((add(orm, Entity_v, entity, key, attr)))
                continue

            if compare(entity_v, entity, attr):
                LOG.warning(
                    "key %d: Exists but last version doesn't match.", entity_id)
                print((add(orm, Entity_v, entity, key, attr)))
                continue
        else:
            if not entity_v:
                LOG.debug("key %d: Doesn't exist and no versions.", entity_id)
                continue

            if len(entity_v_list) == 1:
                if entity_v.existence:
                    LOG.warning(
                        "key %d: Doesn't exist and only one existing version.",
                        entity_id)
                    entity_v_d = add(orm, Entity_v, entity_v, key, attr)
                    entity_v_d.existence = 0
                    entity_v_d.a_time = D_TIME
                else:
                    LOG.error(
                        "key %d: Doesn't exist and only one deleted version. "
                        "Can't fix.",
                        entity_id)
                continue

            if entity_v.existence:
                if not compare(entity_v, entity_v_list[1], attr, True):
                    LOG.warning(
                        "key %d: Doesn't exist and last existing version "
                        "is a copy.",
                        entity_id)
                    entity_v.existence = 0
                    continue

                LOG.warning(
                    "key %d: Doesn't exist and last version exists.", entity_id)
                entity_v_d = add(orm, Entity_v, entity_v, key, attr)
                entity_v_d.existence = 0
                entity_v_d.a_time = D_TIME
                continue

            LOG.debug("OK")
            continue



def cross_results(engine, cross_table, cross_v_table, a_key, a_id, b_key, b_id):
    sql = "select a_time from %s where %s = %d and %s = %d" % (
        cross_table, a_key, a_id, b_key, b_id)
    results = list(engine.execute(sql))
    a_time = results and results[0][0] or None

    sql = """
select distinct a_time, existence
  from %s
  where %s = %d
    and %s = %d
  order by a_time desc
""" % (cross_v_table, a_key, a_id, b_key, b_id)
    results = list(engine.execute(sql))
    versions = [{
        "a_time": float(result[0]),
        "existence": bool(result[1])
    } for result in results]
    return a_time, versions



def add_cross_version(
        engine, cross_v_table, a_key, a_id, b_key, b_id, a_time,
        existence=True
):
    sql = """
insert
  into %s (%s, %s, a_time, existence)
  values (%d, %d, %.3f, %d)
""" % (cross_v_table, a_key, b_key, a_id, b_id, a_time, int(existence))
    engine.execute(sql)



def unexist(engine, cross_v_table, a_key, a_id, b_key, b_id, a_time):
    sql = """
update %s
  set existence = 0
  where %s = %d
    and %s = %d
    and a_time = %.3f
""" % (cross_v_table, a_key, a_id, b_key, b_id, a_time)
    engine.execute(sql)



def audit_cross(orm):
    cross_list = [
        (1, "org", "address"),
        (1, "org", "note"),
        (0, "org", "orgtag"),
        (0, "orgtag", "note"),
        (0, "event", "address"),
        (0, "event", "eventtag"),
        (0, "eventtag", "note"),
        (0, "address", "note"),
        (0, "org", "event"),
        ]

    engine = orm.connection().engine

    for run, a, b in cross_list:
        LOG.info("%s %s", a, b)
        if not run:
            LOG.info(" skipping...")
            continue
        cross_table = "%s_%s" % (a, b)
        cross_v_table = "%s_%s_v" % (a, b)
        a_key = "%s_id" % a
        b_key = "%s_id" % b
        sql = "select distinct %s, %s from %s" % (a_key, b_key, cross_table)
        results = list(engine.execute(sql))
        sql = "select distinct %s, %s from %s" % (a_key, b_key, cross_v_table)
        results += list(engine.execute(sql))
        result_set = set([
            (int(result[0]), int(result[1])) for result in results
        ])

        for a_id, b_id in result_set:
            LOG.debug("%s:%d %s:%d", a_key, a_id, b_key, b_id)
            a_time, versions = cross_results(
                engine, cross_table, cross_v_table, a_key, a_id, b_key, b_id)

            if not a_id or not b_id:
                if a_time:
                    LOG.warning(
                        "%s:%d %s:%d Exists", a_key, a_id, b_key, b_id)
                    continue
                if versions:
                    LOG.warning(
                        "%s:%d %s:%d Versions exist", a_key, a_id, b_key, b_id)
                    continue
                continue

            if a_time:
                if not versions:
                    LOG.warning(
                        "%s:%d %s:%d Exists with no versions",
                        a_key, a_id, b_key, b_id)
                    add_cross_version(
                        engine, cross_v_table, a_key, a_id, b_key, b_id, a_time)
                    continue

                if not versions[0]["existence"]:
                    LOG.warning(
                        "%s:%d %s:%d Exists but last version is deleted",
                        a_key, a_id, b_key, b_id
                    )
                    add_cross_version(
                        engine, cross_v_table, a_key, a_id, b_key, b_id, a_time)
                    continue

                if a_time != versions[0]["a_time"]:
                    LOG.warning(
                        "%s:%d %s:%d Exists but last version a_time "
                        "doesn't match",
                        a_key, a_id, b_key, b_id
                    )
                    add_cross_version(
                        engine, cross_v_table, a_key, a_id, b_key, b_id, a_time)
                    continue
            else:
                if not versions:
                    LOG.debug(
                        "%s:%d %s:%d Doesn't exist and no versions",
                        a_key, a_id, b_key, b_id
                    )
                    continue

                if len(versions) == 1:
                    if versions[0]["existence"]:
                        LOG.warning(
                            "%s:%d %s:%d Doesn't exist and only one "
                            "existing version",
                            a_key, a_id, b_key, b_id
                        )
                        add_cross_version(
                            engine, cross_v_table,
                            a_key, a_id, b_key, b_id, D_TIME, False)
                    else:
                        LOG.warning(
                            "%s:%d %s:%d Doesn't exist and only one "
                            "deleted version. Can't fix.",
                            a_key, a_id, b_key, b_id)
                    continue

                if versions[0]["existence"]:
                    if versions[1]["existence"]:
                        print(versions)
                        if versions[0]["a_time"] == versions[1]["a_time"]:
                            LOG.warning(
                                "%s:%d %s:%d Doesn't exist and last version "
                                "is an exact copy.",
                                a_key, a_id, b_key, b_id)
                            add_cross_version(
                                engine, cross_v_table, a_key, a_id, b_key, b_id,
                                D_TIME, False)
                        else:
                            LOG.warning(
                                "%s:%d %s:%d Doesn't exist and last version "
                                "is a copy.",
                                a_key, a_id, b_key, b_id
                            )
                            unexist(engine, cross_v_table, a_key, a_id,
                                    b_key, b_id, versions[1]["a_time"])
                        continue

                    LOG.warning(
                        "%s:%d %s:%d Doesn't exist and last version exists.",
                        a_key, a_id, b_key, b_id
                    )
                    add_cross_version(
                        engine, cross_v_table,
                        a_key, a_id, b_key, b_id, D_TIME, False)
                    continue
                LOG.debug("OK")
                continue



def audit(orm):
    entity_list = [
        (0, Org, Org_v, "org_id", "org_v_id", [
            "name",
        ]),
        (0, Orgalias, Orgalias_v, "orgalias_id", "orgalias_v_id", [
            "org_id",
            "name",
        ]),
        (0, Orgtag, Orgtag_v, "orgtag_id", "orgtag_v_id", [
            "name",
            "short",
        ]),
        (0, Event, Event_v, "event_id", "event_v_id", [
            "name",
            "start_date", "end_date",
            "description",
            "start_time", "end_time",
        ]),
        (0, Eventtag, Eventtag_v, "eventtag_id", "eventtag_v_id", [
            "name",
            "short",
        ]),
        (0, Address, Address_v, "address_id", "address_v_id", [
            "postal",
            "source",
            "lookup",
            "manual_longitude",
            "manual_latitude",
            "longitude",
            "latitude",
        ]),
        (1, Note, Note_v, "note_id", "note_v_id", [
            "text",
            "source",
        ]),
    ]

    for run, Entity, Entity_v, key, key_v, attr_list in entity_list:
        LOG.info(Entity.__tablename__)
        if not run:
            LOG.info(" skipping...")
            continue
        audit_entity(orm, Entity, Entity_v, key, key_v, attr_list)



def main():
    LOG.addHandler(logging.StreamHandler())

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
        "--configuration", "-c",
        action="store", default=".mango.conf",
        help="Path to configuration file.")
    parser.add_argument(
        "--database", "-d",
        action="store", default="sqlite",
        help="Database target, `sqlite` or `mysql`.")
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Dry run.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)

    connection_url = connection_url_app()
    engine = create_engine(connection_url,)
    session_ = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    orm = session_()

    audit_cross(orm)
    sys.exit(0)

    if args.dry_run:
        LOG.warning("rolling back")
        orm.rollback()
    else:
        LOG.info("Committing.")
        orm.commit()



if __name__ == "__main__":
    main()
