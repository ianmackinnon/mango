# -*- coding: utf-8 -*-

from sqlalchemy import or_
from tornado.web import HTTPError

from base import BaseHandler, authenticated

from base_moderation import \
    get_pending_org_id, \
    get_pending_event_id, \
    get_pending_address_id, \
    get_pending_contact_id, \
    get_pending_org_address_id, \
    get_pending_org_contact_id, \
    get_pending_event_address_id, \
    get_pending_event_contact_id


    
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
                "contact": {},
                }

        for org_id, address_id, org_exists, address_exists in get_pending_org_address_id(self.orm):
            if not org_id in queue["org"]:
                if not org_exists:
                    continue
                queue["org"][org_id] = {
                    "url": "/organisation/%s" % org_id,
                    "revision_url": None,
                    "address": {},
                    "contact": {},
                    }
            address = {
                "url": address_exists and "/address/%s" % address_id,
                "revision_url": "/address/%s/revision" % address_id,
                } 
            queue["org"][org_id]["address"][address_id] = address


        for org_id, contact_id, org_exists, contact_exists in get_pending_org_contact_id(self.orm):
            if not org_id in queue["org"]:
                if not org_exists:
                    continue
                queue["org"][org_id] = {
                    "url": "/organisation/%s" % org_id,
                    "revision_url": None,
                    "address": {},
                    "contact": {},
                    }
            contact = {
                "url": contact_exists and "/contact/%s" % contact_id,
                "revision_url": "/contact/%s/revision" % contact_id,
                } 
            queue["org"][org_id]["contact"][contact_id] = contact
                

        queue["event"] = {}
        for event_id, exists in get_pending_event_id(self.orm):
            queue["event"][event_id] = {
                "url": exists and "/event/%s" % event_id,
                "revision_url": "/event/%s/revision" % event_id,
                "address": {},
                "contact": {},
                }

        for event_id, address_id, event_exists, address_exists in get_pending_event_address_id(self.orm):
            if not event_id in queue["event"]:
                if not event_exists:
                    continue
                queue["event"][event_id] = {
                    "url": "/event/%s" % event_id,
                    "revision_url": None,
                    "address": {},
                    "contact": {},
                    }
            address = {
                "url": address_exists and "/address/%s" % address_id,
                "revision_url": "/address/%s/revision" % address_id,
                } 
            queue["event"][event_id]["address"][address_id] = address

        for event_id, contact_id, event_exists, contact_exists in get_pending_event_contact_id(self.orm):
            if not event_id in queue["event"]:
                if not event_exists:
                    continue
                queue["event"][event_id] = {
                    "url": "/event/%s" % event_id,
                    "revision_url": None,
                    "address": {},
                    "contact": {},
                    }
            contact = {
                "url": contact_exists and "/contact/%s" % contact_id,
                "revision_url": "/contact/%s/revision" % contact_id,
                } 
            queue["event"][event_id]["contact"][contact_id] = contact

        self.render(
            'moderation-queue.html',
            queue=queue,
            )



        


