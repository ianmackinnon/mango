# -*- coding: utf-8 -*-

import json
import datetime

from collections import OrderedDict

from sqlalchemy import distinct, or_, and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy.sql import exists, func, literal
from sqlalchemy.sql.expression import case
from tornado.web import HTTPError

from base import BaseHandler, authenticated, sha1_concat
from note import BaseNoteHandler
from eventtag import BaseEventtagHandler
from address import BaseAddressHandler

from model import Event, Note, Address, Eventtag, event_eventtag, event_address



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
        


class EventListHandler(BaseEventHandler, BaseEventtagHandler):
    @staticmethod
    def _cache_key(name_search, past, tag_name_list, view, visibility):
        if not visibility:
            visibility = "public"
        return sha1_concat(json.dumps({
                "nameSearch": name_search,
                "past": past,
                "tag": tuple(set(tag_name_list)),
                "visibility": visibility,
                "view": view,
                }))
    
    def get(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("nameSearch", None, json=is_json)
        past = self.get_argument_bool("past", None, json=is_json)
        tag_name_list = self.get_arguments("tag", json=is_json)
        location = self.get_argument_geobox("location", None, json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)
        view = self.get_argument_allowed("view", ["event", "marker"],
                                         default="event", json=is_json)

        if self.has_javascript and not self.accept_type("json"):
            self.render(
                'event_list.html',
                name=name,
                name_search=name_search,
                past=past,
                tag_name_list=tag_name_list,
                location=location and location.to_obj(),
                offset=offset,
                )
            return;

        cache_key = None
        if self.accept_type("json") and not location and not offset:
            cache_key = self._cache_key(name_search, past, tag_name_list, view,
                                        self.parameters["visibility"])
            value = self.cache.get(cache_key)
            if value:
                self.write(value)
                self.finish()
                return

        event_packet = self._get_event_packet_search(
            name=name,
            name_search=name_search,
            past=past,
            tag_name_list=tag_name_list,
            location=location,
            visibility=self.parameters["visibility"],
            offset=offset,
            view=view,
            )

        if cache_key:
            self.cache.set(cache_key, json.dumps(event_packet))

        if self.accept_type("json"):
            self.write_json(event_packet)
        else:
            self.render(
                'event_list.html',
                event_packet=event_packet,
                name=name,
                name_search=name_search,
                past=past,
                tag_name_list=tag_name_list,
                location=location and location.to_obj(),
                offset=offset,
                )

    def post(self):
        is_json = self.content_type("application/json")

        name = self.get_argument("name", json=is_json)
        start_date = self.get_argument_date("start_date", json=is_json)
        end_date = self.get_argument_date("end_date", json=is_json)
        description = self.get_argument("description", None, json=is_json);
        start_time = self.get_argument_time("start_time", None, json=is_json)
        end_time = self.get_argument_time("end_time", None, json=is_json)
        public = self.get_argument_public("public", json=is_json)

        event = Event(
            name, start_date, end_date,
            description, start_time, end_time,
            moderation_user=self.current_user, public=public)
        self.orm.add(event)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)



class EventNewHandler(BaseEventHandler):
    def get(self):
        self.render(
            'event.html',
            )



class EventHandler(BaseEventHandler):
    def get(self, event_id_string):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_offset = self.get_argument_int("note_offset", None)

        public = bool(self.current_user)

        event = self._get_event(event_id_string)

        if self.deep_visible():
            org_list=event.org_list
            address_list=event.address_list
            eventtag_list=event.eventtag_list
        else:
            org_list=event.org_list_public
            address_list=event.address_list_public
            eventtag_list=event.eventtag_list_public

        note_list, note_count = event.note_list_filtered(
            note_search=note_search,
            note_order=note_order,
            note_offset=note_offset,
            all_visible=self.deep_visible(),
            )

        org_list = [org.obj(public=public) for org in org_list]
        address_list = [address.obj(public=public) for address in address_list]
        eventtag_list = [eventtag.obj(public=public) for eventtag in eventtag_list]
        note_list = [note.obj(public=public) for note in note_list]

        obj = event.obj(
            public=public,
            org_obj_list=org_list,
            address_obj_list=address_list,
            eventtag_obj_list=eventtag_list,
            note_obj_list=note_list,
            note_count=note_count,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'event.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                )


    @authenticated
    def delete(self, event_id_string):
        event = self._get_event(event_id_string)
        self.orm.delete(event)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + "/event")
        
    @authenticated
    def put(self, event_id_string):
        event = self._get_event(event_id_string)

        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)
        start_date = self.get_argument_date("start_date", json=is_json)
        end_date = self.get_argument_date("end_date", json=is_json)
        description = self.get_argument("description", None, json=is_json);
        start_time = self.get_argument_time("start_time", None, json=is_json)
        end_time = self.get_argument_time("end_time", None, json=is_json)
        public = self.get_argument_public("public", json=is_json)

        if event.name == name and \
                event.start_date == start_date and \
                event.end_date == end_date and \
                event.description == description and \
                event.start_time == start_time and \
                event.end_time == end_time and \
                event.public == public:
            self.redirect(self.next or self.url_root[:-1] + event.url)
            return

        event.name = name
        event.start_date = start_date
        event.end_date = end_date
        event.description = description
        event.start_time = start_time
        event.end_time = end_time
        event.moderation_user = self.current_user
        event.public = public
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)



class EventAddressListHandler(BaseEventHandler, BaseAddressHandler):
    @authenticated
    def get(self, event_id_string):
        public = bool(self.current_user)
        event = self._get_event(event_id_string)
        obj = event.obj(
            public=public,
            )
        self.render(
            'address.html',
            address=None,
            entity=obj,
            entity_list="event_list",
            )
        
    @authenticated
    def post(self, event_id_string):
        event = self._get_event(event_id_string)

        postal, source, lookup, manual_longitude, manual_latitude, \
            public = \
            BaseAddressHandler._get_arguments(self)

        address = Address(postal, source, lookup,
                              manual_longitude=manual_longitude,
                              manual_latitude=manual_latitude,
                              moderation_user=self.current_user,
                              public=public,
                              )
        address.geocode()
        event.address_list.append(address)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)



class EventNoteListHandler(BaseEventHandler, BaseNoteHandler):
    @authenticated
    def post(self, event_id_string):
        event = self._get_event(event_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)
        
        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        event.note_list.append(note)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)

    @authenticated
    def get(self, event_id_string):
        event = self._get_event(event_id_string)
        public = bool(self.current_user)
        obj = event.obj(
            public=public,
            )
        self.next = event.url
        self.render(
            'note.html',
            entity=obj,
            )



class EventAddressHandler(BaseEventHandler, BaseAddressHandler):
    @authenticated
    def put(self, event_id_string, address_id_string):
        event = self._get_event(event_id_string)
        address = self._get_address(address_id_string)
        if address not in event.address_list:
            event.address_list.append(address)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)

    @authenticated
    def delete(self, event_id_string, address_id_string):
        event = self._get_event(event_id_string)
        address = self._get_address(address_id_string)
        if address in event.address_list:
            event.address_list.remove(address)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)



class EventNoteHandler(BaseEventHandler, BaseNoteHandler):
    @authenticated
    def put(self, event_id_string, note_id_string):
        event = self._get_event(event_id_string)
        note = self._get_note(note_id_string)
        if note not in event.note_list:
            event.note_list.append(note)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)

    @authenticated
    def delete(self, event_id_string, note_id_string):
        event = self._get_event(event_id_string)
        note = self._get_note(note_id_string)
        if note in event.note_list:
            event.note_list.remove(note)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)



class EventEventtagListHandler(BaseEventHandler, BaseEventtagHandler):
    @authenticated
    def get(self, event_id_string):

        # event...

        event = self._get_event(event_id_string)

        if self.deep_visible():
            eventtag_list=event.eventtag_list
        else:
            eventtag_list=event.eventtag_list_public

        public = bool(self.current_user)

        eventtag_list = [eventtag.obj(public=public) for eventtag in eventtag_list]

        obj = event.obj(
            public=public,
            eventtag_obj_list=eventtag_list,
            )

        # eventtag...

        eventtag_and_event_count_list, name, short, search = \
            BaseEventtagHandler._get_eventtag_and_event_count_list_search_and_args(self)

        eventtag_list = []
        for eventtag, event_count in eventtag_and_event_count_list:
            eventtag_list.append(eventtag.obj(
                    public=bool(self.current_user),
                    event_len=event_count,
                    ))

        self.render(
            'entity_tag.html',
            obj=obj,
            tag_list=eventtag_list,
            search=search,
            type_title="Event",
            type_title_plural="Events",
            type_url="event",
            type_tag_list="eventtag_list",
            type_entity_list="event_list",
            type_li_template="event_li",
            )



class EventEventtagHandler(BaseEventHandler, BaseEventtagHandler):
    @authenticated
    def put(self, event_id_string, eventtag_id_string):
        event = self._get_event(event_id_string)
        eventtag = self._get_eventtag(eventtag_id_string)
        if eventtag not in event.eventtag_list:
            event.eventtag_list.append(eventtag)
            self.orm.commit()
        print self.next
        self.redirect(self.next or self.url_root[:-1] + event.url)

    @authenticated
    def delete(self, event_id_string, eventtag_id_string):
        event = self._get_event(event_id_string)
        eventtag = self._get_eventtag(eventtag_id_string)
        if eventtag in event.eventtag_list:
            event.eventtag_list.remove(eventtag)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + event.url)





