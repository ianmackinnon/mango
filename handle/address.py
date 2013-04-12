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
    accept_org_address_v, accept_event_address_v



class BaseAddressHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    def _get_address(self, id_string,
                     required=True, future_version=False):
        return self._get_entity(Address, "address_id",
                                "address",
                                id_string,
                                required,
                                )

    def _get_address_v(self, id_string,
                       required=True, future_version=False):
        return self._get_entity_v(Address, "address_id",
                                  Address_v, "address_v_id",
                                  "address",
                                  id_string,
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
    
    def _create_address_v(self, id_):
        return self._create_address(id_, version=True)
    
    def _decline_address_v(self, id_string):
        id_ = int(id_string)

        address = Address_v(
            id_,
            "DECLINED", "DECLINED",
            moderation_user=self.current_user, public=None)
        address.existence = False

        detach(address)
        
        return address

    def _address_history_query(self, address_id_string):
        return self._history_query(
            Address, "address_id",
            Address_v,
            address_id_string)

    def _get_address_history(self, address_id_string):
        address_v_query, address = self._address_history_query(address_id_string)
        
        address_v_query = address_v_query \
            .order_by(Address_v.address_v_id.desc())

        return address_v_query.all(), address

    def _count_address_history(self, address_id_string):
        address_v_query, address = self._address_history_query(address_id_string)

        return address_v_query.count()

    def _get_address_latest_a_time(self, address_id_string):
        id_ = int(address_id_string)
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
            accept_org_address_v,
            accept_event_address_v,
            ]
        for accept in accept_list:
            print accept
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
    def _before_set(self):
        return self._before_address_set

    @property
    def _after_accept_new(self):
        return self._after_address_accept_new

    def get(self, address_id_string):
        note_search, note_order, note_offset = self.get_note_arguments()

        public = self.moderator

        required = True
        if self.current_user:
            address_v = self._get_address_v(address_id_string)
            if address_v:
                required = False
        address = self._get_address(address_id_string, required=required)

        if self.moderator and not address:
            self.next = "%s/revision" % address_v.url
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

        org_list = [org.obj(public=public) for org in org_list]
        event_list = [event.obj(public=public) for event in event_list]
        note_list = [note.obj(public=public) for note in note_list]

        if self.contributor and address_v:
            address = address_v

        obj = address.obj(
            public=public,
            org_obj_list=org_list,
            event_obj_list=event_list,
            note_obj_list=note_list,
            note_count=note_count,
            )

        version_url=None

        if self.current_user and self._count_address_history(address_id_string) > 1:
            version_url="%s/revision" % address.url

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'address.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                version_url=version_url,
                entity_list="entity_list",  # What's this?
                )


class AddressRevisionListHandler(BaseAddressHandler):
    @authenticated
    def get(self, address_id_string):
        address_v_list, address = self._get_address_history(address_id_string)

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
                gravatar_hash=user.auth.gravatar_hash,
                url=address_v.url,
                url_v=address_v.url_v,
                )
            history.append(entity)

        if not history:
            raise HTTPError(404, "%s: No such address" % (address_id_string))

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
    def _get_address_revision(self, address_id_string, address_v_id_string):
        address_id = int(address_id_string)
        address_v_id = int(address_v_id_string)

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
    def get(self, address_id_string, address_v_id_string):
        address_v, address = self._get_address_revision(address_id_string, address_v_id_string)
        
        if not address_v.existence:
            raise HTTPError(404)

        if self.moderator:
            if address and address.a_time == address_v.a_time:
                self.next = address.url
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
            latest_a_time = self._get_address_latest_a_time(address_id_string)
            if latest_a_time and address_v.a_time < latest_a_time:
                raise HTTPError(404)
            if address and newest_address_v.a_time < address.a_time:
                raise HTTPError(404)
            if newest_address_v == address_v:
                self.next = address_v.url
                return self.redirect_next()
            address = newest_address_v

        obj = address and address.obj(
            public=True,
            )

        obj_v = address_v.obj(
            public=True,
            )

        ignore_list = []
        fields = (
            ("postal", "name"),
            ("source", "markdown"),
            ("public", "public")
            )

        if not self.moderator or not address_v.moderation_user.moderator:
            ignore_list.append(
                "public"
                )

        latest_a_time = self._get_address_latest_a_time(address_id_string)

        self.render(
            'revision.html',
            action_url=address_v.url,
            version_url="%s/revision" % (address_v.url),
            version_current_url=address and address.url,
            latest_a_time=latest_a_time,
            fields=fields,
            ignore_list=ignore_list,
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
    def post(self, address_id_string):
        if not self.moderator:
            raise HTTPError(404)

        address = self._get_address(address_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)

        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        address.note_list.append(note)
        self.orm_commit()
        return self.redirect_next(address.url)

    @authenticated
    def get(self, address_id_string):
        if not self.moderator:
            raise HTTPError(404)

        address = self._get_address(address_id_string)

        obj = address.obj(
            public=self.moderator,
            )

        self.render(
            'note.html',
            entity=obj,
            )



class AddressNoteHandler(BaseAddressHandler, BaseNoteHandler):
    @authenticated
    def put(self, address_id_string, note_id_string):
        if not self.moderator:
            raise HTTPError(404)

        address = self._get_address(address_id_string)
        note = self._get_note(note_id_string)
        if note not in address.note_list:
            address.note_list.append(note)
            self.orm_commit()
        return self.redirect_next(address.url)

    @authenticated
    def delete(self, address_id_string, note_id_string):
        if not self.moderator:
            raise HTTPError(404)

        address = self._get_address(address_id_string)
        note = self._get_note(note_id_string)
        if note in address.note_list:
            address.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(address.url)
