# -*- coding: utf-8 -*-

import json

from tornado.web import HTTPError

from base import authenticated, sha1_concat, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from base_event import BaseEventHandler
from base_org import BaseOrgHandler
from base_note import BaseNoteHandler
from eventtag import BaseEventtagHandler
from address import BaseAddressHandler

from model import Event, Note, Address, Org



class EventListHandler(BaseEventHandler, BaseEventtagHandler,
                       MangoEntityListHandlerMixin):
    @property
    def _create(self):
        return self._create_event

    @property
    def _get(self):
        return self._get_event

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
                self.set_header("Content-Type", "application/json; charset=UTF-8")
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



class EventNewHandler(BaseEventHandler):
    @authenticated
    def get(self):
        self.render(
            'event.html',
            )



class EventHandler(BaseEventHandler, MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_event

    @property
    def _get(self):
        return self._get_event

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
        self.redirect(event.url)



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
        self.redirect(event.url)

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
        self.redirect(event.url)

    @authenticated
    def delete(self, event_id_string, address_id_string):
        event = self._get_event(event_id_string)
        address = self._get_address(address_id_string)
        if address in event.address_list:
            event.address_list.remove(address)
            self.orm.commit()
        self.redirect(event.url)



class EventNoteHandler(BaseEventHandler, BaseNoteHandler):
    @authenticated
    def put(self, event_id_string, note_id_string):
        event = self._get_event(event_id_string)
        note = self._get_note(note_id_string)
        if note not in event.note_list:
            event.note_list.append(note)
            self.orm.commit()
        self.redirect(event.url)

    @authenticated
    def delete(self, event_id_string, note_id_string):
        event = self._get_event(event_id_string)
        note = self._get_note(note_id_string)
        if note in event.note_list:
            event.note_list.remove(note)
            self.orm.commit()
        self.redirect(event.url)



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
        self.redirect(event.url)

    @authenticated
    def delete(self, event_id_string, eventtag_id_string):
        event = self._get_event(event_id_string)
        eventtag = self._get_eventtag(eventtag_id_string)
        if eventtag in event.eventtag_list:
            event.eventtag_list.remove(eventtag)
            self.orm.commit()
        self.redirect(event.url)



class EventOrgListHandler(BaseEventHandler, BaseOrgHandler):
    @authenticated
    def get(self, event_id_string):

        is_json = self.content_type("application/json")

        # event...

        event = self._get_event(event_id_string)

        if self.deep_visible():
            org_list=event.org_list
        else:
            org_list=event.org_list_public
            
        public = bool(self.current_user)

        org_list = [org.obj(public=public) for org in org_list]

        obj = event.obj(
            public=public,
            org_obj_list=org_list,
            )

        del org_list

        # org...

        org_name_search = self.get_argument("search", None, json=is_json)

        org_alias_name_query = BaseOrgHandler._get_org_alias_search_query(
            self,
            name_search=org_name_search,
            visibility=self.parameters["visibility"]
            )

        org_list = []
        org_count = org_alias_name_query.count()
        for org, alias in org_alias_name_query[:20]:
            org_list.append(org.obj(
                    public=bool(self.current_user),
                    alias=alias and alias.obj(
                        public=bool(self.current_user),
                        ),
                    ))

        self.next = event.url
        self.render(
            'event_organisation.html',
            obj=obj,
            org_list=org_list,
            org_count=org_count,
            search=org_name_search,
            )



class EventOrgHandler(BaseEventHandler, BaseOrgHandler):
    @authenticated
    def put(self, event_id_string, org_id_string):
        event = self._get_event(event_id_string)
        org = self._get_org(org_id_string)
        if org not in event.org_list:
            event.org_list.append(org)
            self.orm.commit()
        self.redirect(event.url)

    @authenticated
    def delete(self, event_id_string, org_id_string):
        event = self._get_event(event_id_string)
        org = self._get_org(org_id_string)
        if org in event.org_list:
            event.org_list.remove(org)
            self.orm.commit()
        self.redirect(event.url)



class EventDuplicateHandler(BaseEventHandler):
    @authenticated
    def post(self, event_id_string):
        event = self._get_event(event_id_string)

        is_json = self.content_type("application/json")
        start_date = self.get_argument_date("start_date", json=is_json)

        end_date = start_date + (event.end_date - event.start_date)

        name = event.name
        description = event.description
        start_time = event.start_time
        end_time = event.end_time
        public = event.public

        event2 = Event(
            name, start_date, end_date,
            description, start_time, end_time,
            moderation_user=self.current_user, public=public)
        self.orm.add(event2)

        for address in event.address_list:
            address2 = Address(
                address.postal,
                address.source,
                address.lookup,
                manual_longitude=address.manual_longitude,
                manual_latitude=address.manual_latitude,
                moderation_user=self.current_user,
                public=address.public)
            address2.geocode()
            event2.address_list.append(address2)

        for eventtag in event.eventtag_list:
            event2.eventtag_list.append(eventtag)

        for note in event.note_list:
            note2 = Note(
                note.text,
                note.source,
                moderation_user=self.current_user,
                public=note.public)
            event2.note_list.append(note2)

        for org in event.org_list:
            event2.org_list.append(org)

        self.orm.commit()
        self.redirect(event2.url)
