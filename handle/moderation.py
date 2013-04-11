# -*- coding: utf-8 -*-

from sqlalchemy import or_
from tornado.web import HTTPError

from base import BaseHandler, authenticated

from model import User

from model_v import Org_v, Event_v, Address_v, \
    org_address_v, event_address_v



def get_pending_entity_id(orm,
                          Entity_v,
                          ):
        latest = orm.query(Entity_v.entity_id.label("entity_id"), Entity_v.moderation_user_id) \
            .order_by(Entity_v.entity_v_id.desc()) \
            .subquery()

        latest = orm.query(latest.c.entity_id, latest.c.moderation_user_id) \
            .group_by(latest.c.entity_id) \
            .subquery()

        results = orm.query(latest.c.entity_id) \
            .join((User, User.user_id == latest.c.moderation_user_id)) \
            .filter(User.moderator == False) \
            .limit(20)

        return [id_ for (id_, ) in results]



def get_pending_org_id(orm):
    return get_pending_entity_id(orm, Org_v)



def get_pending_event_id(orm):
    return get_pending_entity_id(orm, Event_v)



def get_pending_address_id(orm):
    return get_pending_entity_id(orm, Address_v)



def get_pending_org_address_id(orm):
    address_id_list = get_pending_entity_id(orm, Address_v)

    query = orm.query(org_address_v.c.org_id, org_address_v.c.address_id) \
        .filter(org_address_v.c.address_id.in_(address_id_list)) \
        .group_by(org_address_v.c.org_id, org_address_v.c.address_id)

    return query.all()



def get_pending_event_address_id(orm):
    address_id_list = get_pending_entity_id(orm, Address_v)

    query = orm.query(event_address_v.c.event_id, event_address_v.c.address_id) \
        .filter(event_address_v.c.address_id.in_(address_id_list)) \
        .group_by(event_address_v.c.event_id, event_address_v.c.address_id)

    return query.all()



class ModerationQueueHandler(BaseHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        queue = {}

        queue["org"] = {}
        for org_id in get_pending_org_id(self.orm):
            queue["org"][org_id] = {
                "url": "/organisation/%s" % org_id,
                "revision_url": "/organisation/%s/revision" % org_id,
                "address": {},
                }

        for org_id, address_id in get_pending_org_address_id(self.orm):
            if not org_id in queue["org"]:
                queue["org"][org_id] = {
                    "url": "/organisation/%s" % org_id,
                    "revision_url": None,
                    "address": {},
                    }
            address = {
                "url": "/address/%s" % address_id,
                "revision_url": "/address/%s/revision" % address_id,
                } 
            queue["org"][org_id]["address"][address_id] = address
                

        queue["event"] = {}
        for event_id in get_pending_event_id(self.orm):
            queue["event"][event_id] = {
                "url": "/event/%s" % org_id,
                "revision_url": "/event/%s/revision" % event_id,
                "address": {},
                }

        for event_id, address_id in get_pending_event_address_id(self.orm):
            if not event_id in queue["event"]:
                queue["event"][event_id] = {
                    "url": "/eventanisation/%s" % event_id,
                    "revision_url": None,
                    "address": {},
                    }
            address = {
                "url": "/address/%s" % address_id,
                "revision_url": "/address/%s/revision" % address_id,
                } 
            queue["event"][event_id]["address"][address_id] = address
                

        self.render(
            'moderation-queue.html',
            queue=queue,
            )



        


