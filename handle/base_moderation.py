
from sqlalchemy import alias
from sqlalchemy.inspection import inspect
from sqlalchemy.sql.expression import and_, exists

from model import User, Org, Event, Address, Contact, \
    org_address

from model_v import Org_v, Event_v, Address_v, Contact_v, \
    org_address_v, event_address_v, \
    org_contact_v, event_contact_v



def get_pending_entity_id(orm, Entity_v, Entity, desc_attr):
    # pylint: disable=invalid-name,singleton-comparison
    # Allow `Entity_v` and `Entity` as abstract class names.
    # Cannot use `is` in SQLAlchemy filters

    Entity_v2 = alias(Entity_v)
    entity_id_name = inspect(Entity).primary_key[0].name
    entity_v_id_name = inspect(Entity_v).primary_key[0].name

    # "order by" and "group by" together give undefined results
    # in MySQL, so we have to use a "not exists" query.

    latest = orm.query(
        Entity_v.entity_id.label("entity_id"),
        getattr(Entity_v, desc_attr).label("desc"),
        Entity_v.moderation_user_id
    ) \
        .filter(~exists().where(and_(
            Entity_v2.c[entity_id_name] == Entity_v.entity_id,
            Entity_v2.c[entity_v_id_name] > Entity_v.entity_v_id
        ))) \
        .subquery()

    latest = orm.query(
        latest.c.entity_id,
        latest.c.desc,
        latest.c.moderation_user_id
    ) \
        .group_by(latest.c.entity_id) \
        .subquery()

    results = orm.query(latest.c.entity_id, latest.c.desc) \
        .join((User, User.user_id == latest.c.moderation_user_id)) \
        .outerjoin((Entity, Entity.entity_id == latest.c.entity_id)) \
        .add_columns(Entity.entity_id, getattr(Entity, desc_attr), User.name) \
        .filter(User.moderator == False) \
        .limit(20)

    results = list(results)
    for i, row in enumerate(results):
        row = list(row)
        row[2] = bool(row[2])
        results[i] = row

    return results



def get_pending_org_id(orm):
    return get_pending_entity_id(orm, Org_v, Org, "name")



def get_pending_event_id(orm):
    return get_pending_entity_id(orm, Event_v, Event, "name")



def get_pending_address_id(orm):
    return get_pending_entity_id(orm, Address_v, Address, "postal")



def get_pending_contact_id(orm):
    return get_pending_entity_id(orm, Contact_v, Contact, "text")



def has_pending(orm):
    count = 0
    for f in [
            get_pending_org_id,
            get_pending_event_id,
            get_pending_address_id,
            get_pending_contact_id
    ]:
        pending = f(orm)
        count += len(pending)
    return count



def has_address_not_found(orm):
    # pylint: disable=singleton-comparison
    # Cannot use `is` in SQLAlchemy filters

    return orm.query(Org, Address) \
        .join(org_address) \
        .join(Address) \
        .filter(and_(
            Org.public == True,
            Address.public == True,
            Address.latitude == None,
        )) \
        .count()



def dict_by_first(list_):
    dict_ = {}
    for row in list_:
        dict_[row[0]] = row
    return dict_



def get_pending_parent_entity_id(
        orm,
        get_pending_entity_id_,
        parent_entity_v,
        Parent, parent_id, parent_desc, entity_id,
):
    # pylint: disable=invalid-name
    # Allow abstract `Parent`.

    entity_id_list = dict_by_first(get_pending_entity_id_(orm))

    if not entity_id_list:
        return []

    query = orm.query(
        getattr(parent_entity_v.c, parent_id),
        getattr(parent_entity_v.c, entity_id)
    ) \
        .outerjoin(Parent, getattr(Parent, parent_id) ==
                   getattr(parent_entity_v.c, parent_id)) \
        .add_columns(
            getattr(Parent, parent_id),
            getattr(Parent, parent_desc)
        ) \
        .filter(
            getattr(parent_entity_v.c, entity_id).in_(
                list(entity_id_list.keys()))
        ) \
        .distinct()

    results = []
    removed = set()
    for _j, (parent_id, entity_id,
             parent_exists, parent_desc) in enumerate(query.all()):
        (entity_id, entity_desc_new, entity_exists,
         entity_desc_old, user_name) = entity_id_list[entity_id]
        removed.add(entity_id)
        results.append((
            parent_id, parent_desc, bool(parent_exists),
            entity_id, entity_desc_new, entity_exists,
            entity_desc_old, user_name
        ))

    for entity_id in removed:
        del entity_id_list[entity_id]

    for _key, _value in list(entity_id_list.items()):
        # Parent doesn't exist, or isn't of type 'parent'
        pass

    return results



def get_pending_org_address_id(orm):
    return get_pending_parent_entity_id(
        orm,
        get_pending_address_id,
        org_address_v,
        Org, "org_id", "name", "address_id",
    )

def get_pending_org_contact_id(orm):
    return get_pending_parent_entity_id(
        orm,
        get_pending_contact_id,
        org_contact_v,
        Org, "org_id", "name", "contact_id",
    )

def get_pending_event_address_id(orm):
    return get_pending_parent_entity_id(
        orm,
        get_pending_address_id,
        event_address_v,
        Event, "event_id", "name", "address_id",
    )

def get_pending_event_contact_id(orm):
    return get_pending_parent_entity_id(
        orm,
        get_pending_contact_id,
        event_contact_v,
        Event, "event_id", "name", "contact_id",
    )
