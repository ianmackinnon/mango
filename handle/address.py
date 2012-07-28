# -*- coding: utf-8 -*-
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
from tornado.web import HTTPError

import geo

from base import BaseHandler, authenticated
from note import BaseNoteHandler

from model import Address, Note, Org, Orgtag



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

        public = bool(self.current_user)

        if self.deep_visible():
            options = (
                joinedload("org_list"),
                joinedload("note_list"),
                )
        else:
            options = (
                joinedload("org_list_public"),
                joinedload("note_list_public"),
                )

        address = self._get_address(address_id_string, options=options)

        if self.deep_visible():
            org_list=address.org_list
            note_list=address.note_list
        else:
            org_list=address.org_list_public
            note_list=address.note_list_public

        org_list = [org.obj(public=public) for org in org_list]
        note_list = [note.obj(public=public) for note in note_list]

        obj = address.obj(
            public=public,
            org_obj_list=org_list,
            note_obj_list=note_list,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'address.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                )

    @authenticated
    def put(self, address_id_string):
        address = self._get_address(address_id_string)

        postal, source, lookup, manual_longitude, manual_latitude, \
            public, note_id_list = \
            BaseAddressHandler._get_arguments(self)

        if address.postal == postal and \
                address.source == source and \
                address.lookup == lookup and \
                address.manual_longitude == manual_longitude and \
                address.manual_latitude == manual_latitude and \
                address.public == public:
            self.redirect(self.next or address.url)
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
        self.redirect(self.next or address.url)



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
        self.redirect(self.next or address.url)

    def get(self, address_id_string):
        address = self._get_address(address_id_string)
        self.next = address.url
        self.render(
            'note.html',
            entity=address
            )



class AddressNoteHandler(BaseAddressHandler, BaseNoteHandler):
    @authenticated
    def put(self, address_id_string, note_id_string):
        address = self._get_address(address_id_string)
        note = self._get_note(note_id_string)
        if note not in address.note_list:
            address.note_list.append(note)
            self.orm.commit()
        self.redirect(self.next or address.url)

    @authenticated
    def delete(self, address_id_string, note_id_string):
        address = self._get_address(address_id_string)
        note = self._get_note(note_id_string)
        if note in address.note_list:
            address.note_list.remove(note)
            self.orm.commit()
        self.redirect(self.next or address.url)
