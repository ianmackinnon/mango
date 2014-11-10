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

        queue = {
            "org": {},
            "event": {},
        }


        for org_id, desc_new, exists, desc_old, user_name in get_pending_org_id(self.orm):
            queue["org"][org_id] = {
                "url": exists and "/organisation/%s" % org_id,
                "revision_url": "/organisation/%s/revision" % org_id,
                "description": desc_old or desc_new,
                "user": user_name,
                "address": {},
                "contact": {},
                }

        for row in get_pending_org_address_id(self.orm):
            org_id, org_desc, org_exists = row[:3]
            address_id, address_desc_new, address_exists, address_desc_old, user_name = row[3:]
            if not org_id in queue["org"]:
                if not org_exists:
                    continue
                queue["org"][org_id] = {
                    "url": "/organisation/%s" % org_id,
                    "revision_url": None,
                    "description": org_desc,
                    "user": None,
                    "address": {},
                    "contact": {},
                    }
            address = {
                "url": address_exists and "/address/%s" % address_id,
                "revision_url": "/address/%s/revision" % address_id,
                "description": address_desc_old or address_desc_new,
                "user": user_name,
                } 
            queue["org"][org_id]["address"][address_id] = address

        for row in get_pending_org_contact_id(self.orm):
            org_id, org_desc, org_exists = row[:3]
            contact_id, contact_desc_new, contact_exists, contact_desc_old, user_name = row[3:]
            if not org_id in queue["org"]:
                if not org_exists:
                    continue
                queue["org"][org_id] = {
                    "url": "/organisation/%s" % org_id,
                    "revision_url": None,
                    "description": org_desc,
                    "user": None,
                    "address": {},
                    "contact": {},
                    }
            contact = {
                "url": contact_exists and "/contact/%s" % contact_id,
                "revision_url": "/contact/%s/revision" % contact_id,
                "description": contact_desc_old or contact_desc_new,
                "user": user_name,
                } 
            queue["org"][org_id]["contact"][contact_id] = contact

        

        for event_id, desc_new, exists, desc_old, user_name in get_pending_event_id(self.orm):
            queue["event"][event_id] = {
                "url": exists and "/event/%s" % event_id,
                "revision_url": "/event/%s/revision" % event_id,
                "description": desc_old or desc_new,
                "user": user_name,
                "address": {},
                "contact": {},
                }

        for row in get_pending_event_address_id(self.orm):
            event_id, event_desc, event_exists = row[:3]
            address_id, address_desc_new, address_exists, address_desc_old, user_name = row[3:]
            if not event_id in queue["event"]:
                if not event_exists:
                    continue
                queue["event"][event_id] = {
                    "url": "/eventanisation/%s" % event_id,
                    "revision_url": None,
                    "description": event_desc,
                    "user": None,
                    "address": {},
                    "contact": {},
                    }
            address = {
                "url": address_exists and "/address/%s" % address_id,
                "revision_url": "/address/%s/revision" % address_id,
                "description": address_desc_old or address_desc_new,
                "user": user_name,
                } 
            queue["event"][event_id]["address"][address_id] = address

        for row in get_pending_event_contact_id(self.orm):
            event_id, event_desc, event_exists = row[:3]
            contact_id, contact_desc_new, contact_exists, contact_desc_old, user_name = row[3:]
            if not event_id in queue["event"]:
                if not event_exists:
                    continue
                queue["event"][event_id] = {
                    "url": "/eventanisation/%s" % event_id,
                    "revision_url": None,
                    "description": event_desc,
                    "user": None,
                    "address": {},
                    "contact": {},
                    }
            contact = {
                "url": contact_exists and "/contact/%s" % contact_id,
                "revision_url": "/contact/%s/revision" % contact_id,
                "description": contact_desc_old or contact_desc_new,
                "user": user_name,
                } 
            queue["event"][event_id]["contact"][contact_id] = contact


        self.render(
            'moderation-queue.html',
            queue=queue,
            )

