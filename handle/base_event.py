# -*- coding: utf-8 -*-



import datetime

from collections import OrderedDict

from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from tornado.web import HTTPError

from base import BaseHandler


from model import Event, Address, Eventtag



max_address_per_page = 26
max_address_pages = 3



class BaseEventHandler(BaseHandler):
    def _get_event(self, event_id_string, options=None):
        event_id = int(event_id_string)

        query = self.orm.query(Event)\
            .filter_by(event_id=event_id)

        if options:
            query = query \
                .options(*options)

        if not self.current_user:
            query = query \
                .filter_by(public=True)

        try:
            event = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d: No such event" % event_id)

        return event

    def _get_event_packet_search(self, name=None, name_search=None,
                                 past=False,
                                 tag_name_list=None,
                                 location=None,
                                 visibility=None,
                                 offset=None,
                                 view="event"):
        event_query = self.orm.query(Event)

        date_start = None
        date_end = None
        today = datetime.datetime.today().date()
        if past:
            date_end = today
        else:
            date_start = today

        if date_start:
            event_query = event_query.filter(Event.start_date >= date_start)
        if date_end:
            event_query = event_query.filter(Event.end_date <= date_end)

        event_query = self.filter_visibility(event_query, Event, visibility)

        if name:
            event_query = event_query.filter_by(name=name)
        elif name_search:
            event_query = event_query\
                .filter(Event.name.contains(name_search))

        if tag_name_list:
            event_query = event_query.join((Eventtag, Event.eventtag_list)) \
                .filter(Eventtag.short.in_(tag_name_list))

        if location:
            event_address_query = event_query \
                .join(Event.address_list)
        else:
            event_address_query = event_query \
                .outerjoin(Event.address_list)
            
        event_address_query = event_address_query \
            .add_entity(Address)
        event_address_query = self.filter_visibility(
            event_address_query, Address, visibility,
            secondary=True, null_column=Address.address_id)

        if location:
            event_address_query = event_address_query \
                .filter(and_(
                    Address.latitude != None,
                    Address.latitude >= location.south,
                    Address.latitude <= location.north,
                    Address.longitude != None,
                    Address.longitude >= location.west,
                    Address.longitude <= location.east,
                    ))

        if past:
            event_address_query = event_address_query \
                .order_by(Event.start_date.desc())
        else:
            event_address_query = event_address_query \
                .order_by(Event.end_date.asc())

        if offset:
            event_address_query = event_address_query \
                .offset(offset)

        event_packet = {
            "location": location and location.to_obj(),
            }

        if (view == "marker" or
            event_address_query.count() > max_address_per_page * max_address_pages
            ):
            event_packet["marker_list"] = []
            for event, address in event_address_query:
                event_packet["marker_list"].append({
                        "name": event.name,
                        "url": event.url,
                        "latitude": address and address.latitude,
                        "longitude": address and address.longitude,
                        })
        else:
            events = OrderedDict()
            for event, address in event_address_query:
                if not event.event_id in events:
                    events[event.event_id] = {
                        "event": event,
                        "address_obj_list": [],
                        }
                if address:
                    events[event.event_id]["address_obj_list"].append(address.obj(
                            public=bool(self.current_user),
                            general=True,
                            ))

            event_packet["event_list"] = []
            for event_id, data in events.items():
                event_packet["event_list"].append(data["event"].obj(
                        public=bool(self.current_user),
                        address_obj_list=data["address_obj_list"],
                        ))

        return event_packet
        


