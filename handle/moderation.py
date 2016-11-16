
from tornado.web import HTTPError

from handle.base import BaseHandler, authenticated

from handle.base_moderation import \
    get_pending_org_id, \
    get_pending_event_id, \
    get_pending_org_address_id, \
    get_pending_org_contact_id, \
    get_pending_event_address_id, \
    get_pending_event_contact_id



class ModerationQueueHandler(BaseHandler):
    def parent_entity_rows(
            self,
            queue,
            get_pending_parent_entity_id,
            parent,
            entity,
            parent_url,
            entity_url,
            child_name_list,
    ):
        for row in get_pending_parent_entity_id(self.orm):
            (parent_id, parent_desc, parent_exists) = row[:3]
            (entity_id, entity_desc_new, entity_exists,
             entity_desc_old, user_name) = row[3:]
            if parent_id not in queue[parent]:
                if not parent_exists:
                    # parent doesn't exist (may have been declined)
                    continue
                queue[parent][parent_id] = {
                    "url": "/%s/%s" % (parent_url, parent_id),
                    "revisionUrl": None,
                    "description": parent_desc,
                    "user": None,
                    }
                for child_name in child_name_list:
                    queue[parent][parent_id][child_name] = {}

            entity_dict = {
                "url": entity_exists and "/%s/%s" % (entity_url, entity_id),
                "revisionUrl": "/%s/%s/revision" % (entity_url, entity_id),
                "description": entity_desc_old or entity_desc_new,
                "user": user_name,
                }
            queue[parent][parent_id][entity][entity_id] = entity_dict

    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        queue = {
            "org": {},
            "event": {},
        }


        for (org_id, desc_new, exists,
             desc_old, user_name) in get_pending_org_id(self.orm):
            queue["org"][org_id] = {
                "url": exists and "/organisation/%s" % org_id,
                "revisionUrl": "/organisation/%s/revision" % org_id,
                "description": desc_old or desc_new,
                "user": user_name,
                "address": {},
                "contact": {},
                }

        self.parent_entity_rows(
            queue, get_pending_org_address_id,
            "org", "address", "organisation", "address", ["address", "contact"]
        )

        self.parent_entity_rows(
            queue, get_pending_org_contact_id,
            "org", "contact", "organisation", "contact", ["address", "contact"]
        )

        for (event_id, desc_new, exists,
             desc_old, user_name) in get_pending_event_id(self.orm):
            queue["event"][event_id] = {
                "url": exists and "/event/%s" % event_id,
                "revisionUrl": "/event/%s/revision" % event_id,
                "description": desc_old or desc_new,
                "user": user_name,
                "address": {},
                "contact": {},
                }

        self.parent_entity_rows(
            queue, get_pending_event_address_id,
            "event", "address", "event", "address", ["address", "contact"]
        )

        self.parent_entity_rows(
            queue, get_pending_event_contact_id,
            "event", "contact", "event", "contact", ["address", "contact"]
        )

        self.render(
            'moderation-queue.html',
            queue=queue,
            )
