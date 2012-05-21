# -*- coding: utf-8 -*-

import geo

from sqlalchemy.sql import func

from base import BaseHandler, authenticated
from model import Address, Note



class BaseAddressHandler(BaseHandler):
    def _get_arguments(self):
        if self.content_type("application/x-www-form-urlencoded"):
            postal = self.get_argument("postal")
            lookup = self.get_argument("lookup", None)
            manual_longitude = self.get_argument_float("manual_longitude", None)
            manual_latitude = self.get_argument_float("manual_latitude", None)
            note_e_list = [
                int(note_id) for note_id in self.get_arguments("note_id")
                ]
        elif self.content_type("application/json"):
            postal = self.get_json_argument("postal")
            lookup = self.get_json_argument("lookup", None)
            manual_longitude = self.get_json_argument_float("manual_longitude", None)
            manual_latitude = self.get_json_argument_float("manual_latitude", None)
            note_e_list = self.get_json_argument("note_id", [])
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")
        return postal, lookup, manual_longitude, manual_latitude, note_e_list



class AddressListHandler(BaseAddressHandler):
    def get(self):
        lookup = self.get_argument("lookup", None)
        latitude_min = self.get_argument_float("latitude_min", None)
        latitude_max = self.get_argument_float("latitude_max", None)
        longitude_min = self.get_argument_float("longitude_min", None)
        longitude_max = self.get_argument_float("longitude_max", None)
        latitude = self.get_argument_float("latitude", None)
        longitude = self.get_argument_float("longitude", None)

        address_list = Address.query_latest(self.orm)
        
        if latitude_min is not None and latitude_max is not None and \
                longitude_min is not None and longitude_max is not None:
            address_list = address_list \
                .filter(Address.latitude >= latitude_min) \
                .filter(Address.latitude <= latitude_max) \
                .filter(Address.longitude >= longitude_min) \
                .filter(Address.longitude <= longitude_max)
        else:
            if (latitude is None or longitude is None) and lookup:
                coords = geo.geocode(lookup)
                if coords:
                    latitude, longitude = coords
                    print lookup, latitude, longitude
                else:
                    self.messages.append(("WARNING", "Could not find address: '%s'." % lookup))
            if latitude is not None and longitude is not None:
                address_list = address_list \
                    .filter(Address.latitude != None) \
                    .filter(Address.longitude != None) \
                    .order_by(
                    func.abs(latitude - Address.latitude) + \
                    func.abs(longitude - Address.longitude)
                    )

        address_list = address_list.limit(10).all()

        self.render(
            'address_list.html',
            address_list=address_list,
            )



class AddressHandler(BaseAddressHandler):
        
    def get(self, address_e_string, address_id_string):
        address_e = int(address_e_string)
        address_id = address_id_string and int(address_id_string) or None

        if address_id:
            if not self.current_user:
                return self.error(404, "Not found")
            query = self.orm.query(Address).filter_by(address_e=address_e).filter_by(address_id=address_id)
            error = "%d, %d: No such address, version" % (address_e, address_id)
        else:
            query = Address.query_latest(self.orm).filter_by(address_e=address_e)
            error = "%d: No such address" % address_e

        try:
            address = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, error)

        if self.accept_type("json"):
            self.write_json(address.obj())
        else:
            self.render(
                'address.html',
                address=address
                )

    @authenticated
    def put(self, address_e_string, address_id_string):
        if address_id_string:
            return self.error(405, "Cannot edit revisions.")

        address_e = int(address_e_string)

        query = Address.query_latest(self.orm).filter_by(address_e=address_e)

        try:
            address = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such address" % address_e)

        postal, lookup, manual_longitude, manual_latitude, note_e_list = \
            BaseAddressHandler._get_arguments(self)

        if address.postal == postal and \
                address.lookup == lookup and \
                address.manual_longitude == manual_longitude and \
                address.manual_latitude == manual_latitude and \
                set(note_e_list) == set([note.note_e for note in address.note_list()]):
            self.redirect(address.url)
            return
            
        new_address = address.copy(moderation_user=self.current_user)
        new_address.postal = postal
        new_address.lookup = lookup
        new_address.manual_longitude = manual_longitude
        new_address.manual_latitude = manual_latitude
        del new_address.note_entity_list[:]

        if note_e_list:
            note_list = Note.query_latest(self.orm)\
                .filter(Note.note_e.in_(note_e_list))\
                .all()
            for note in note_list:
                new_address.note_entity_list.append(note)

        new_address.geocode()
        self.orm.commit()
        self.redirect(new_address.url)






