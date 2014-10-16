# -*- coding: utf-8 -*-

from sqlalchemy.sql.expression import and_

from model import User, Org, Event, Address, Contact, \
    org_address

from model_v import Org_v, Event_v, Address_v, Contact_v, \
    org_address_v, event_address_v, \
    org_contact_v, event_contact_v



def get_pending_entity_id(orm,
                          Entity_v,
                          Entity,
                          ):
        latest = orm.query(Entity_v.entity_id.label("entity_id"), Entity_v.moderation_user_id) \
            .order_by(Entity_v.entity_v_id.desc()) \
            .subquery()

        latest = orm.query(latest.c.entity_id, latest.c.moderation_user_id) \
            .group_by(latest.c.entity_id) \
            .subquery()

        results = orm.query(latest.c.entity_id) \
            .join((User, User.user_id == latest.c.moderation_user_id)) \
            .outerjoin((Entity, Entity.entity_id == latest.c.entity_id)) \
            .add_columns(Entity.entity_id) \
            .filter(User.moderator == False) \
            .limit(20)

        return [(id_1, bool(id_2)) for (id_1, id_2) in results]



def get_pending_org_id(orm):
    return get_pending_entity_id(orm, Org_v, Org)



def get_pending_event_id(orm):
    return get_pending_entity_id(orm, Event_v, Event)



def get_pending_address_id(orm):
    return get_pending_entity_id(orm, Address_v, Address)



def get_pending_contact_id(orm):
    return get_pending_entity_id(orm, Contact_v, Contact)



def has_pending(orm):
    for f in [get_pending_org_id, get_pending_event_id, get_pending_address_id, get_pending_contact_id]:
        if f(orm):
            return True
    return False



def has_address_not_found(orm):
    return bool(
        orm.query(Org, Address) \
        .join(org_address) \
        .join(Address) \
        .filter(and_(
            Org.public==True,
            Address.public==True,
            Address.latitude==None,
        )) \
        .count()
    )



def get_pending_org_address_id(orm):
    address_id_list = dict(get_pending_entity_id(orm, Address_v, Address))

    query = orm.query(org_address_v.c.org_id, org_address_v.c.address_id) \
        .filter(org_address_v.c.address_id.in_(address_id_list.keys())) \
        .outerjoin((Org, Org.org_id == org_address_v.c.org_id)) \
        .add_columns(Org.org_id) \
        .distinct()
    
    results = []
    for org_id, address_id, org_exists in query.all():
        results.append((org_id, address_id, bool(org_exists), address_id_list[address_id]))

    return results



def get_pending_org_contact_id(orm):
    contact_id_list = dict(get_pending_entity_id(orm, Contact_v, Contact))

    query = orm.query(org_contact_v.c.org_id, org_contact_v.c.contact_id) \
        .filter(org_contact_v.c.contact_id.in_(contact_id_list.keys())) \
        .outerjoin((Org, Org.org_id == org_contact_v.c.org_id)) \
        .add_columns(Org.org_id) \
        .distinct()
    
    results = []
    for org_id, contact_id, org_exists in query.all():
        results.append((org_id, contact_id, bool(org_exists), contact_id_list[contact_id]))

    return results



def get_pending_event_address_id(orm):
    address_id_list = dict(get_pending_entity_id(orm, Address_v, Address))

    query = orm.query(event_address_v.c.event_id, event_address_v.c.address_id) \
        .filter(event_address_v.c.address_id.in_(address_id_list.keys())) \
        .outerjoin((Event, Event.event_id == event_address_v.c.event_id)) \
        .add_columns(Event.event_id) \
        .distinct()
    
    results = []
    for event_id, address_id, event_exists in query.all():
        results.append((event_id, address_id, bool(event_exists), address_id_list[address_id]))

    return results



def get_pending_event_contact_id(orm):
    contact_id_list = dict(get_pending_entity_id(orm, Contact_v, Contact))

    query = orm.query(event_contact_v.c.event_id, event_contact_v.c.contact_id) \
        .filter(event_contact_v.c.contact_id.in_(contact_id_list.keys())) \
        .outerjoin((Event, Event.event_id == event_contact_v.c.event_id)) \
        .add_columns(Event.event_id) \
        .distinct()
    
    results = []
    for event_id, contact_id, event_exists in query.all():
        results.append((event_id, contact_id, bool(event_exists), contact_id_list[contact_id]))

    return results



