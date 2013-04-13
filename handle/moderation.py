# -*- coding: utf-8 -*-

from sqlalchemy import or_
from tornado.web import HTTPError

from base import BaseHandler, authenticated

from model import User, Org, Event, Address

from model_v import Org_v, Event_v, Address_v, \
    org_address_v, event_address_v


    
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



class ModerationQueueHandler(BaseHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        queue = {}

        queue["org"] = {}
        for org_id, exists in get_pending_org_id(self.orm):
            queue["org"][org_id] = {
                "url": exists and "/organisation/%s" % org_id,
                "revision_url": "/organisation/%s/revision" % org_id,
                "address": {},
                }

        for org_id, address_id, org_exists, address_exists in get_pending_org_address_id(self.orm):
            if not org_id in queue["org"]:
                if not org_exists:
                    continue
                queue["org"][org_id] = {
                    "url": "/organisation/%s" % org_id,
                    "revision_url": None,
                    "address": {},
                    }
            address = {
                "url": address_exists and "/address/%s" % address_id,
                "revision_url": "/address/%s/revision" % address_id,
                } 
            queue["org"][org_id]["address"][address_id] = address
                

        queue["event"] = {}
        for event_id, exists in get_pending_event_id(self.orm):
            queue["event"][event_id] = {
                "url": exists and "/event/%s" % event_id,
                "revision_url": "/event/%s/revision" % event_id,
                "address": {},
                }

        for event_id, address_id, event_exists, address_exists in get_pending_event_address_id(self.orm):
            if not event_id in queue["event"]:
                if not event_exists:
                    continue
                queue["event"][event_id] = {
                    "url": "/event/%s" % event_id,
                    "revision_url": None,
                    "address": {},
                    }
            address = {
                "url": address_exists and "/address/%s" % address_id,
                "revision_url": "/address/%s/revision" % address_id,
                } 
            queue["event"][event_id]["address"][address_id] = address

        self.render(
            'moderation-queue.html',
            queue=queue,
            )



        


