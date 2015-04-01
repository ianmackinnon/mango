# -*- coding: utf-8 -*-

import datetime

from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import literal
from sqlalchemy import Unicode
from tornado.web import HTTPError

import geo

from base import BaseHandler, authenticated, \
    HistoryEntity, \
    MangoEntityHandlerMixin, \
    MangoBaseEntityHandlerMixin

from note import BaseNoteHandler

from model import User, Address, Note, Org, Orgtag, Event, \
    org_address, event_address, detach

from model_v import Address_v, \
    accept_address_org_v, accept_address_event_v, \
    org_address_v, event_address_v, \
    mango_entity_append_suggestion

from handle.user import get_user_pending_address_event, get_user_pending_address_org



class BaseAddressHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    def _get_address(self, address_id, required=True):
        return self._get_entity(Address, "address_id",
                                "address",
                                address_id,
                                required,
                                )

    def _get_address_v(self, address_v_id):
        return self._get_entity_v(Address, "address_id",
                                  Address_v, "address_v_id",
                                  "address",
                                  address_v_id,
                                  )

    def _touch_address(self, address_id):
        return self._touch_entity(Address, "address_id",
                                "address",
                                  self._decline_address_v,
                                address_id,
                                )

    def _create_address(self, id_=None, version=False):
        is_json = self.content_type("application/json")
        
        postal = self.get_argument("postal", json=is_json)
        source = self.get_argument("source", json=is_json)
        lookup = self.get_argument("lookup", None, json=is_json)
        manual_longitude = self.get_argument_float("manual_longitude", None, json=is_json)
        manual_latitude = self.get_argument_float("manual_latitude", None, json=is_json)

        public, moderation_user = self._create_revision()

        if version:
            address = Address_v(
                id_,
                postal, source,
                lookup,
                manual_longitude, manual_latitude,
                moderation_user=moderation_user, public=public)
        else:
            address = Address(
                postal, source,
                lookup,
                manual_longitude, manual_latitude,
                moderation_user=moderation_user, public=public)
            
            if id_:
                address.address_id = id_

        detach(address)
        
        return address
    
    def _create_address_v(self, address_id):
        return self._create_address(address_id, version=True)
    
    @staticmethod
    def _decline_address_v(address_id, moderation_user):
        address = Address_v(
            address_id,
            u"DECLINED", u"DECLINED",
            moderation_user=moderation_user, public=None)
        address.existence = False

        detach(address)
        
        return address

    def _address_history_query(self, address_id):
        return self._history_query(
            Address, "address_id",
            Address_v,
            address_id)

    def _get_address_history(self, address_id):
        address_v_query, address = self._address_history_query(address_id)
        
        address_v_query = address_v_query \
            .order_by(Address_v.address_v_id.desc())

        return address_v_query.all(), address

    def _count_address_history(self, address_id):
        address_v_query, address = self._address_history_query(address_id)

        return address_v_query.count()

    def _get_address_latest_a_time(self, id_):
        address_v = self.orm.query(Address_v.a_time) \
            .join((User, Address_v.moderation_user)) \
            .filter(Address_v.address_id == id_) \
            .filter(User.moderator == True) \
            .order_by(Address_v.address_v_id.desc()) \
            .first()

        return address_v and address_v.a_time or None

    def _before_address_set(self, address):
        address.geocode()

    def _after_address_accept_new(self, address):
        accept_list = [
            accept_address_org_v,
            accept_address_event_v,
            ]
        for accept in accept_list:
            if accept(self.orm, address.address_id):
                break



class AddressHandler(BaseAddressHandler, MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_address

    @property
    def _create_v(self):
        return self._create_address_v

    @property
    def _decline_v(self):
        return self._decline_address_v

    @property
    def _get(self):
        return self._get_address

    @property
    def _get_v(self):
        return self._get_address_v

    @property
    def _touch(self):
        return self._touch_address

    @property
    def _before_set(self):
        return self._before_address_set

    @property
    def _after_accept_new(self):
        return self._after_address_accept_new

    def get(self, address_id):
        note_search, note_order, note_offset = self.get_note_arguments()

        public = self.moderator

        required = True
        address_v = None
        if self.current_user:
            address_v = self._get_address_v(address_id)
            if address_v:
                required = False
        address = self._get_address(address_id, required=required)

        if self.moderator and not address:
            self.next_ = "%s/revision" % address_v.url
            return self.redirect_next()

        if address:
            if self.deep_visible():
                org_list=address.org_list
                event_list=address.event_list
            else:
                org_list=address.org_list_public
                event_list=address.event_list_public
                
            note_list, note_count = address.note_list_filtered(
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                all_visible=self.deep_visible()
                )
        else:
            org_list=[]
            event_list=[]
            note_list=[]
            note_count = 0

        if self.contributor:
            address_id = address and address.address_id or address_v.address_id

            mango_entity_append_suggestion(
                self.orm, org_list, get_user_pending_address_org,
                self.current_user, address_id, "org_id")
            mango_entity_append_suggestion(
                self.orm, event_list, get_user_pending_address_event,
                self.current_user, address_id, "event_id")

        org_list = [org.obj(public=public) for org in org_list]
        event_list = [event.obj(public=public) for event in event_list]
        note_list = [note.obj(public=public) for note in note_list]

        edit_block = False
        if address_v:
            if self.contributor:
                address = address_v
            else:
                edit_block = True

        obj = address.obj(
            public=public,
            org_list=org_list,
            event_list=event_list,
            note_list=note_list,
            note_count=note_count,
            )

        version_url=None

        if self.current_user and self._count_address_history(address_id) > 1:
            version_url="%s/revision" % address.url

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            entity = None
            if obj:
                parent_list = obj["org_list"] + obj["event_list"]
                entity = len(parent_list) == 1 and parent_list[0] or None
            self.load_map = True
            self.render(
                'address.html',
                obj=obj,
                entity=entity,
                edit_block=edit_block,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                version_url=version_url,
                )


class AddressRevisionListHandler(BaseAddressHandler):
    @authenticated
    def get(self, address_id):
        address_v_list, address = self._get_address_history(address_id)

        history = []
        for address_v in address_v_list:
            user = address_v.moderation_user

            is_latest = False
            if self.moderator:
                if address and address.a_time == address_v.a_time:
                    is_latest = True
            else:
                if not history:
                    is_latest = True

            entity = HistoryEntity(
                type="address",
                entity_id=address_v.address_id,
                entity_v_id=address_v.address_v_id,
                date=address_v.a_time,
                existence=bool(address),
                existence_v=address_v.existence,
                is_latest=is_latest,
                public=address_v.public,
                name=address_v.postal,
                user_id=user.user_id,
                user_name=user.name,
                user_moderator=user.moderator,
                gravatar_hash=user.gravatar_hash(),
                url=address_v.url,
                url_v=address_v.url_v,
                )
            history.append(entity)

        if not history:
            raise HTTPError(404, "%s: No such address" % (address_id))

        if not self.moderator:
            if len(history) == int(bool(address)):
                raise HTTPError(404)
        
        version_current_url = (address and address.url) or (not self.moderator and history and history[-1].url)

        self.render(
            'revision-history.html',
            entity=True,
            version_current_url=version_current_url,
            latest_a_time=address and address.a_time,
            title_text="Revision History",
            history=history,
            )
        


class AddressRevisionHandler(BaseAddressHandler):
    def _get_address_revision(self, address_id, address_v_id):
        query = self.orm.query(Address_v) \
            .filter_by(address_id=address_id) \
            .filter_by(address_v_id=address_v_id)

        try:
            address_v = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d:%d: No such address revision" % (address_id, address_v_id))

        query = self.orm.query(Address) \
            .filter_by(address_id=address_id)

        try:
            address = query.one()
        except NoResultFound:
            address = None

        return address_v, address

    @authenticated
    def get(self, address_id, address_v_id):
        address_v, address = self._get_address_revision(address_id, address_v_id)
        
        if not address_v.existence:
            raise HTTPError(404)

        if self.moderator:
            if address and address.a_time == address_v.a_time:
                self.next_ = address.url
                return self.redirect_next()
        else:
            if not ((address_v.moderation_user == self.current_user) or \
                        (address and address_v.a_time == address.a_time)):
                raise HTTPError(404)
            newest_address_v = self.orm.query(Address_v) \
                .filter_by(moderation_user=self.current_user) \
                .order_by(Address_v.address_v_id.desc()) \
                .first()
            if not newest_address_v:
                raise HTTPError(404)
            latest_a_time = self._get_address_latest_a_time(address_id)
            if latest_a_time and address_v.a_time < latest_a_time:
                raise HTTPError(404)
            if address and newest_address_v.a_time < address.a_time:
                raise HTTPError(404)
            if newest_address_v == address_v:
                self.next_ = address_v.url
                return self.redirect_next()
            address = newest_address_v

        obj = address and address.obj(
            public=True,
            )

        obj_v = address_v.obj(
            public=True,
            )

        fields = (
            ("postal", "name"),
            ("source", "markdown"),
            ("public", "public")
            )

        latest_a_time = self._get_address_latest_a_time(address_id)

        self.render(
            'revision.html',
            action_url=address_v.url,
            version_url="%s/revision" % (address_v.url),
            version_current_url=address and address.url,
            latest_a_time=latest_a_time,
            fields=fields,
            obj=obj,
            obj_v=obj_v,
            )
        


class AddressEntityListHandler(BaseHandler):
    def get(self):
        key = "address:%s" % ["public", "all"][self.deep_visible()]

        value = self.cache.get(key)
        if value:
            self.write(value)
            return

        address_list = self.orm.query(
            Address.address_id,
            func.coalesce(Address.latitude, Address.manual_latitude),
            func.coalesce(Address.longitude, Address.manual_longitude),
            ).filter(func.coalesce(
                Address.latitude, Address.manual_latitude,
                Address.longitude, Address.manual_longitude
                ) != None);

        org_list = address_list \
            .join((org_address,
                   Address.address_id == org_address.c.address_id)) \
            .join((Org, Org.org_id == org_address.c.org_id)) \
            .add_columns(Org.org_id, Org.name, literal("org"))

        event_list = address_list \
            .join((event_address,
                   Address.address_id == event_address.c.address_id)) \
            .join((Event, Event.event_id == event_address.c.event_id)) \
            .add_columns(Event.event_id, Event.name, literal("event"))

        today = datetime.datetime.now().date()
        event_list = event_list.filter(Event.start_date >= today)

        if not (self.moderator and self.deep_visible()):
            org_list = org_list.filter(Org.public==True)
            event_list = event_list.filter(Event.public==True)
        
        address_list = org_list.union(event_list)

        obj_list = []
        for result in address_list.all():
            obj_list.append(dict(zip(
                        ["address_id", "latitude", "longitude", "entity_id", "name", "entity"],
                        result)))

        value = self.dump_json(obj_list)
        self.cache.set(key, value)

        self.write(value)



class AddressLookupHandler(BaseAddressHandler):
    def get(self):
        is_json = self.content_type("application/json")
        postal = self.get_argument("postal", json=is_json)
        lookup = self.get_argument("lookup", None, json=is_json)

        address = Address(postal, None, lookup)
        address.geocode()

        self.write_json(address.obj(
                public=self.moderator,
                ))



class AddressNoteListHandler(BaseAddressHandler, BaseNoteHandler):
    @authenticated
    def post(self, address_id):
        if not self.moderator:
            raise HTTPError(404)

        address = self._get_address(address_id)
        note = self._create_note()

        address.note_list.append(note)
        self.orm_commit()
        return self.redirect_next(address.url)

    @authenticated
    def get(self, address_id):
        if not self.moderator:
            raise HTTPError(404)

        address = self._get_address(address_id)

        obj = address.obj(
            public=self.moderator,
            )

        self.render(
            'note.html',
            entity=obj,
            )



class AddressNoteHandler(BaseAddressHandler, BaseNoteHandler):
    @authenticated
    def put(self, address_id, note_id):
        if not self.moderator:
            raise HTTPError(404)

        address = self._get_address(address_id)
        note = self._get_note(note_id)
        if note not in address.note_list:
            address.note_list.append(note)
            self.orm_commit()
        return self.redirect_next(address.url)

    @authenticated
    def delete(self, address_id, note_id):
        if not self.moderator:
            raise HTTPError(404)

        address = self._get_address(address_id)
        note = self._get_note(note_id)
        if note in address.note_list:
            address.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(address.url)



class ModerationAddressNotFoundHandler(BaseHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        is_json = self.content_type("application/json")

        query = self.orm.query(Org, Address) \
                .join(org_address) \
                .join(Address) \
                .filter(and_(
                    Org.public==True,
                    Address.public==True,
                    Address.latitude==None,
                ))

        data = []
        for org, address in query.all():
            data.append((
                org.obj(
                    public=self.moderator,
                ),
                address.obj(
                    public=self.moderator,
                )
            ))

        self.render(
            'moderation-address-not-found.html',
            data=data,
            )

