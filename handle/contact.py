# -*- coding: utf-8 -*-

import datetime

from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import literal
from sqlalchemy import Unicode
from tornado.web import HTTPError

from base import BaseHandler, authenticated, \
    HistoryEntity, \
    MangoEntityHandlerMixin, \
    MangoBaseEntityHandlerMixin

from model import User, Medium, Contact, Org, Event, \
    org_contact, event_contact, detach

from model_v import Contact_v, \
    accept_contact_org_v, accept_contact_event_v, \
    org_contact_v, event_contact_v, \
    mango_entity_append_suggestion

from handle.user import get_user_pending_contact_event, get_user_pending_contact_org



class BaseContactHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    def _get_contact(self, contact_id, required=True):
        return self._get_entity(Contact, "contact_id",
                                "contact",
                                contact_id,
                                required,
                                )

    def _get_contact_v(self, contact_v_id):
        return self._get_entity_v(Contact, "contact_id",
                                  Contact_v, "contact_v_id",
                                  "contact",
                                  contact_v_id,
                                  )

    def _touch_contact(self, contact_id):
        return self._touch_entity(Contact, "contact_id",
                                  "contact",
                                  self._decline_contact_v,
                                  contact_id,
                              )

    def _create_contact(self, id_=None, version=False):
        # pylint: disable=maybe-no-member
        # (`self.get_argument` appears to return list)

        is_json = self.content_type("application/json")
        
        medium_name = self.get_argument("medium", json=is_json)

        text = self.get_argument("text", json=is_json)
        description = self.get_argument("description", None, json=is_json)
        source = self.get_argument("source", None, json=is_json)
        public, moderation_user = self._create_revision()

        if medium_name == "Twitter" and text.startswith("@"):
            text = text[1:]

        try:
            medium = self.orm.query(Medium) \
                .filter_by(name=medium_name) \
                .one()
        except NoResultFound:
            raise HTTPError(404, "%s: No such medium" % medium_name)

        if version:
            contact = Contact_v(
                id_,
                medium,
                text, description, source,
                moderation_user=moderation_user, public=public)
        else:
            contact = Contact(
                medium,
                text, description, source,
                moderation_user=moderation_user, public=public)
            
            if id_:
                contact.contact_id = id_

        contact.medium_id = medium.medium_id
        detach(contact)
        
        return contact
    
    def _create_contact_v(self, contact_id):
        return self._create_contact(contact_id, version=True)
    
    @staticmethod
    def _decline_contact_v(contact_id, moderation_user):
        contact = Contact_v(
            contact_id,
            None, # medium
            u"DECLINED",
            moderation_user=moderation_user, public=None)
        contact.existence = False

        detach(contact)
        
        return contact

    def _contact_history_query(self, contact_id):
        return self._history_query(
            Contact, "contact_id",
            Contact_v,
            contact_id)

    def _get_contact_history(self, contact_id):
        contact_v_query, contact = self._contact_history_query(contact_id)
        
        contact_v_query = contact_v_query \
            .order_by(Contact_v.contact_v_id.desc())

        return contact_v_query.all(), contact

    def _count_contact_history(self, contact_id):
        contact_v_query, contact = self._contact_history_query(contact_id)

        return contact_v_query.count()

    def _get_contact_latest_a_time(self, id_):
        contact_v = self.orm.query(Contact_v.a_time) \
            .join((User, Contact_v.moderation_user)) \
            .filter(Contact_v.contact_id == id_) \
            .filter(User.moderator == True) \
            .order_by(Contact_v.contact_v_id.desc()) \
            .first()

        return contact_v and contact_v.a_time or None

    def _before_contact_set(self, contact):
        pass

    def _after_contact_accept_new(self, contact):
        accept_list = [
            accept_contact_org_v,
            accept_contact_event_v,
            ]
        for accept in accept_list:
            if accept(self.orm, contact.contact_id):
                break

    @property
    def medium_list(self):
        results = self.orm.query(Medium.name).all()
        results = [result.name for result in results]
        return results



class ContactHandler(BaseContactHandler, MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_contact

    @property
    def _create_v(self):
        return self._create_contact_v

    @property
    def _decline_v(self):
        return self._decline_contact_v

    @property
    def _get(self):
        return self._get_contact

    @property
    def _get_v(self):
        return self._get_contact_v

    @property
    def _touch(self):
        return self._touch_contact

    @property
    def _before_set(self):
        return self._before_contact_set

    @property
    def _after_accept_new(self):
        return self._after_contact_accept_new

    def get(self, contact_id):
        public = self.moderator

        required = True
        contact_v = None
        if self.current_user:
            contact_v = self._get_contact_v(contact_id)
            if contact_v:
                required = False
        contact = self._get_contact(contact_id, required=required)

        if self.moderator and not contact:
            self.next_ = "%s/revision" % contact_v.url
            return self.redirect_next()

        if contact:
            if self.deep_visible():
                org_list=contact.org_list
                event_list=contact.event_list
            else:
                org_list=contact.org_list_public
                event_list=contact.event_list_public
        else:
            org_list=[]
            event_list=[]

        if self.contributor:
            contact_id = contact and contact.contact_id or contact_v.contact_id

            mango_entity_append_suggestion(
                self.orm, org_list, get_user_pending_contact_org,
                self.current_user, contact_id, "org_id")
            mango_entity_append_suggestion(
                self.orm, event_list, get_user_pending_contact_event,
                self.current_user, contact_id, "event_id")

        org_list = [org.obj(public=public) for org in org_list]
        event_list = [event.obj(public=public) for event in event_list]

        edit_block = False
        if contact_v:
            if self.contributor:
                contact = contact_v
            else:
                edit_block = True

        obj = contact.obj(
            public=public,
            medium=contact.medium.name,
            org_list=org_list,
            event_list=event_list,
            )

        version_url=None

        if self.current_user and self._count_contact_history(contact_id) > 1:
            version_url="%s/revision" % contact.url

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            entity = None
            if obj:
                parent_list = obj["orgList"] + obj["eventList"]
                entity = len(parent_list) == 1 and parent_list[0] or None
            self.render(
                'contact.html',
                obj=obj,
                entity=entity,
                medium_list=self.medium_list,
                edit_block=edit_block,
                version_url=version_url,
                )


class ContactRevisionListHandler(BaseContactHandler):
    @authenticated
    def get(self, contact_id):
        contact_v_list, contact = self._get_contact_history(contact_id)

        history = []
        for contact_v in contact_v_list:
            user = contact_v.moderation_user

            is_latest = False
            if self.moderator:
                if contact and contact.a_time == contact_v.a_time:
                    is_latest = True
            else:
                if not history:
                    is_latest = True

            entity = HistoryEntity(
                type="contact",
                entity_id=contact_v.contact_id,
                entity_v_id=contact_v.contact_v_id,
                date=contact_v.a_time,
                existence=bool(contact),
                existence_v=contact_v.existence,
                is_latest=is_latest,
                public=contact_v.public,
                name=contact_v.text,
                user_id=user.user_id,
                user_name=user.name,
                user_moderator=user.moderator,
                gravatar_hash=user.gravatar_hash(),
                url=contact_v.url,
                url_v=contact_v.url_v,
                )
            history.append(entity)

        if not history:
            raise HTTPError(404, "%s: No such contact" % (contact_id))

        if not self.moderator:
            if len(history) == int(bool(contact)):
                raise HTTPError(404)
        
        version_current_url = (contact and contact.url) or (not self.moderator and history and history[-1].url)

        self.render(
            'revision-history.html',
            entity=True,
            version_current_url=version_current_url,
            latest_a_time=contact and contact.a_time,
            title_text="Revision History",
            history=history,
            )
        


class ContactRevisionHandler(BaseContactHandler):
    def _get_contact_revision(self, contact_id, contact_v_id):
        query = self.orm.query(Contact_v) \
            .filter_by(contact_id=contact_id) \
            .filter_by(contact_v_id=contact_v_id)

        try:
            contact_v = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d:%d: No such contact revision" % (contact_id, contact_v_id))

        query = self.orm.query(Contact) \
            .filter_by(contact_id=contact_id)

        try:
            contact = query.one()
        except NoResultFound:
            contact = None

        return contact_v, contact

    @authenticated
    def get(self, contact_id, contact_v_id):
        contact_v, contact = self._get_contact_revision(contact_id, contact_v_id)
        
        if not contact_v.existence:
            raise HTTPError(404)

        if self.moderator:
            if contact and contact.a_time == contact_v.a_time:
                self.next_ = contact.url
                return self.redirect_next()
        else:
            if not ((contact_v.moderation_user == self.current_user) or \
                        (contact and contact_v.a_time == contact.a_time)):
                raise HTTPError(404)
            newest_contact_v = self.orm.query(Contact_v) \
                .filter_by(moderation_user=self.current_user) \
                .order_by(Contact_v.contact_v_id.desc()) \
                .first()
            if not newest_contact_v:
                raise HTTPError(404)
            latest_a_time = self._get_contact_latest_a_time(contact_id)
            if latest_a_time and contact_v.a_time < latest_a_time:
                raise HTTPError(404)
            if contact and newest_contact_v.a_time < contact.a_time:
                raise HTTPError(404)
            if newest_contact_v == contact_v:
                self.next_ = contact_v.url
                return self.redirect_next()
            contact = newest_contact_v

        obj = contact and contact.obj(
            public=True,
            medium=contact.medium.name,
            )

        obj_v = contact_v.obj(
            public=True,
            medium=contact_v.medium.name,
            )

        fields = (
            ("medium", "name"),
            ("text", "name"),
            ("description", "name"),
            ("source", "markdown"),
            ("public", "public")
            )

        latest_a_time = self._get_contact_latest_a_time(contact_id)

        self.render(
            'revision.html',
            action_url=contact_v.url,
            version_url="%s/revision" % (contact_v.url),
            version_current_url=contact and contact.url,
            latest_a_time=latest_a_time,
            fields=fields,
            obj=obj,
            obj_v=obj_v,
            )
        


