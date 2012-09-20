# -*- coding: utf-8 -*-

import datetime

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import literal
from sqlalchemy import Unicode
from tornado.web import HTTPError

import geo

from base import BaseHandler, authenticated
from note import BaseNoteHandler

from model import Address, Note, Org, Orgtag, Event, \
    org_address, event_address



class BaseAddressHandler(BaseHandler):
    def _get_address(self, address_id_string, options=None):
        address_id = int(address_id_string)
        
        query = self.orm.query(Address).\
            filter_by(address_id=address_id)

        if options:
            query = query \
                .options(*options)

        if not self.current_user:
            query = query \
                .filter_by(public=True)

        try:
            address = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d: No such address" % address_id)

        return address

    def _get_arguments(self):
        is_json = self.content_type("application/json")
        postal = self.get_argument("postal", json=is_json)
        source = self.get_argument("source", json=is_json)
        lookup = self.get_argument("lookup", None, json=is_json)
        manual_longitude = self.get_argument_float("manual_longitude", None, json=is_json)
        manual_latitude = self.get_argument_float("manual_latitude", None, json=is_json)
        public = self.get_argument_public("public", json=is_json)
        return (postal, source, lookup, manual_longitude, manual_latitude, public)



class AddressHandler(BaseAddressHandler):
    def get(self, address_id_string):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_offset = self.get_argument_int("note_offset", None)

        public = bool(self.current_user)

        address = self._get_address(address_id_string)

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

        org_list = [org.obj(public=public) for org in org_list]
        event_list = [event.obj(public=public) for event in event_list]
        note_list = [note.obj(public=public) for note in note_list]

        obj = address.obj(
            public=public,
            org_obj_list=org_list,
            event_obj_list=event_list,
            note_obj_list=note_list,
            note_count=note_count,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'address.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                entity_list="entity_list",
                )

    @authenticated
    def put(self, address_id_string):
        address = self._get_address(address_id_string)

        postal, source, lookup, manual_longitude, manual_latitude, \
            public = \
            BaseAddressHandler._get_arguments(self)

        if address.postal == postal and \
                address.source == source and \
                address.lookup == lookup and \
                address.manual_longitude == manual_longitude and \
                address.manual_latitude == manual_latitude and \
                address.public == public:
            self.redirect(self.next or self.url_root[:-1] + address.url)
            return
            
        address.postal = postal
        address.source = source
        address.lookup = lookup
        address.manual_longitude = manual_longitude
        address.manual_latitude = manual_latitude
        address.public = public
        address.moderation_user = self.current_user

        address.geocode()
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + address.url)



class AddressListHandler(BaseAddressHandler):
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

        if not self.deep_visible():
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

        self.write_json(address.obj(public=bool(self.current_user)))



class AddressNoteListHandler(BaseAddressHandler, BaseNoteHandler):
    @authenticated
    def post(self, address_id_string):
        address = self._get_address(address_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)

        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        address.note_list.append(note)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + address.url)

    def get(self, address_id_string):
        address = self._get_address(address_id_string)

        public = bool(self.current_user)

        obj = address.obj(
            public=public,
            )

        self.render(
            'note.html',
            entity=obj,
            )



class AddressNoteHandler(BaseAddressHandler, BaseNoteHandler):
    @authenticated
    def put(self, address_id_string, note_id_string):
        address = self._get_address(address_id_string)
        note = self._get_note(note_id_string)
        if note not in address.note_list:
            address.note_list.append(note)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + address.url)

    @authenticated
    def delete(self, address_id_string, note_id_string):
        address = self._get_address(address_id_string)
        note = self._get_note(note_id_string)
        if note in address.note_list:
            address.note_list.remove(note)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + address.url)
