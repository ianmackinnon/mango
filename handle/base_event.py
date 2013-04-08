# -*- coding: utf-8 -*-

import datetime

from collections import OrderedDict

from sqlalchemy import and_, or_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from tornado.web import HTTPError

from base import BaseHandler, MangoBaseEntityHandlerMixin

from model import Event, Address, Eventtag, detach

from model_v import Event_v


max_address_per_page = 26
max_address_pages = 3



class BaseEventHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    def _get_event(self, id_string,
                   required=True, future_version=False):
        return self._get_entity(Event, "event", "event_id",
                                Event_v, "event_v", "event_v_id",
                                id_string,
                                required, future_version
                                )

    def _create_event(self, id_=None, version=False):
        is_json = self.content_type("application/json")

        name = self.get_argument("name", json=is_json)
        start_date = self.get_argument_date("start_date", json=is_json)
        end_date = self.get_argument_date("end_date", None, json=is_json)
        description = self.get_argument("description", None, json=is_json);
        start_time = self.get_argument_time("start_time", None, json=is_json)
        end_time = self.get_argument_time("end_time", None, json=is_json)

        if end_date is None:
            end_date = start_date

        if end_time and not start_time:
            raise HTTPError(400, "End time only allowed if start time is also supplied.")

        if end_date < start_date:
            raise HTTPError(400, "End date is earlier than start date.")
        if end_date == start_date and start_time and end_time and end_time < start_time:
            raise HTTPError(400, "End time is earlier than start time on the same date.")

        public, moderation_user = self._create_revision()

        if version:
            event = Event_v(
                id_,
                name, start_date, end_date,
                description, start_time, end_time,
                moderation_user=moderation_user, public=public)
        else:
            event = Event(
                name, start_date, end_date,
                description, start_time, end_time,
                moderation_user=moderation_user, public=public)
            
            if id_:
                event.event_id = id_

        detach(event)

        return event
    
    def _create_event_v(self, id_):
        return self._create_event(id_, version=True)

    def _event_history_query(self, event_id_string):
        return self._history_query(
            Event, "event_id",
            Event_v,
            event_id_string)

    def _get_event_history(self, event_id_string):
        event_v_query, event = self._event_history_query(event_id_string)
        
        event_v_query = event_v_query \
            .order_by(Event_v.a_time.desc())

        return event_v_query.all(), event

    def _count_event_history(self, event_id_string):
        event_v_query, event = self._event_history_query(event_id_string)

        return event_v_query.count() - int(bool(event))

    def _get_event_search_query(
        self, name=None, name_search=None,
        tag_name_list=None, visibility=None):
        
        event_query = self.orm.query(Event)
        event_query = self.filter_visibility(event_query, Event, visibility)

        if name:
            event_query = event_query.filter_by(name=name)
        elif name_search:
            name_column = func.lower(Event.name)
            name_value = name_search.lower()
            event_query = event_query\
                .filter(name_column.contains(name_value))

        if tag_name_list:
            event_query = event_query.join((Eventtag, Event.eventtag_list)) \
                .filter(Eventtag.base_short.in_(tag_name_list))
            # order by?

        return event_query



    def _get_event_packet_search(self, name=None, name_search=None,
                                 past=False,
                                 tag_name_list=None,
                                 location=None,
                                 visibility=None,
                                 offset=None,
                                 map_view="entity"):

        event_query = self._get_event_search_query(
            name=name, name_search=name_search,
            tag_name_list=tag_name_list, visibility=visibility)

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

        if (map_view == "marker" or
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
                            public=self.moderator,
                            general=True,
                            ))

            event_packet["event_list"] = []
            for event_id, data in events.items():
                event = data["event"]
                address_obj_list = data["address_obj_list"]
                address_obj_list.sort(
                    key=lambda address_obj: address_obj.get("latitude", None),
                    reverse=True
                    )
                eventtag_obj_list = [eventtag.obj(public=True) for eventtag in event.eventtag_list_public]
                event_packet["event_list"].append(event.obj(
                        public=self.moderator,
                        address_obj_list=address_obj_list,
                        eventtag_obj_list=eventtag_obj_list,
                        ))

        return event_packet
        


