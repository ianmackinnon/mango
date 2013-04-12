# -*- coding: utf-8 -*-

import json

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import or_, and_
from tornado.web import HTTPError

from base import authenticated, sha1_concat, \
    HistoryEntity, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from base_event import BaseEventHandler
from base_org import BaseOrgHandler
from base_note import BaseNoteHandler
from eventtag import BaseEventtagHandler
from address import BaseAddressHandler

from model import Event, Note, Address, Org

from model_v import Event_v, Address_v

from handle.user import get_user_pending_event_address



class EventListHandler(BaseEventHandler, BaseEventtagHandler,
                       MangoEntityListHandlerMixin):
    Entity = Event
    Entity_v = Event_v
    entity_id = "event_id"
    entity_v_id = "event_v_id"

    @property
    def _create(self):
        return self._create_event

    @property
    def _create_v(self):
        return self._create_event_v

    @property
    def _get(self):
        return self._get_event

    @staticmethod
    def _cache_key(name_search, past, tag_name_list, map_view, visibility):
        if not visibility:
            visibility = "public"
        return sha1_concat(json.dumps({
                "nameSearch": name_search,
                "past": past,
                "tag": tuple(set(tag_name_list)),
                "visibility": visibility,
                "mapView": map_view,
                }))
    
    def get(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("nameSearch", None, json=is_json)
        past = self.get_argument_bool("past", None, json=is_json)
        tag_name_list = self.get_arguments("tag", json=is_json)
        location = self.get_argument_geobox("location", None, json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)
        map_view = self.get_argument_allowed("mapView", ["entity", "marker"],
                                             default="entity", json=is_json)

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
        if 0 and self.accept_type("json") and not location and not offset:
            cache_key = self._cache_key(
                name_search, past,
                tag_name_list, map_view,
                self.parameters.get("visibility", None),
                )
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
            visibility=self.parameters.get("visibility", None),
            offset=offset,
            map_view=map_view,
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


class DiaryHandler(EventListHandler):
    def get(self):
        event_packet = self._get_event_packet_search(
            past=False,
            visibility=True,
            )

        self.render(
            'diary.html',
            event_packet=event_packet,
            )



class EventNewHandler(BaseOrgHandler):
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
    def _create_v(self):
        return self._create_event_v

    @property
    def _decline_v(self):
        return self._decline_event_v

    @property
    def _get(self):
        return self._get_event

    def get(self, event_id_string):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_offset = self.get_argument_int("note_offset", None)

        public = self.moderator

        required = True
        if self.current_user:
            event_v = self._get_event_v(event_id_string)
            if event_v:
                required = False
        event = self._get_event(event_id_string, required=required)

        if self.moderator and not event:
            self.next = "%s/revision" % event_v.url
            return self.redirect_next()

        if event:
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
        else:
            org_list=[]
            address_list=[]
            eventtag_list=[]
            note_list=[]
            note_count = 0

        if self.contributor:
            event_id = event and event.event_id or event_v.event_id
            
            for address_v in get_user_pending_event_address(
                self.orm, self.current_user, event_id):
                
                for a, address in enumerate(address_list):
                    if address.address_id == address_v.address_id:
                        address_list[a] = address_v
                        break
                else:
                    address_list.append(address_v)

        org_list = [org.obj(public=public) for org in org_list]
        address_list = [address.obj(public=public) for address in address_list]
        eventtag_list = [eventtag.obj(public=public) for eventtag in eventtag_list]
        note_list = [note.obj(public=public) for note in note_list]

        if self.contributor and event_v:
            event = event_v

        obj = event.obj(
            public=public,
            org_obj_list=org_list,
            address_obj_list=address_list,
            eventtag_obj_list=eventtag_list,
            note_obj_list=note_list,
            note_count=note_count,
            )

        version_url=None

        if self.current_user and self._count_event_history(event_id_string) > 1:
            version_url="%s/revision" % event.url

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'event.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                version_url=version_url,
                )



class EventRevisionListHandler(BaseEventHandler):
    @authenticated
    def get(self, event_id_string):
        event_v_list, event = self._get_event_history(event_id_string)

        history = []
        for event_v in event_v_list:
            user = event_v.moderation_user

            is_latest = False
            if self.moderator:
                if event and event.a_time == event_v.a_time:
                    is_latest = True
            else:
                if not history:
                    is_latest = True

            entity = HistoryEntity(
                type="event",
                entity_id=event_v.event_id,
                entity_v_id=event_v.event_v_id,
                date=event_v.a_time,
                existence=bool(event),
                existence_v=event_v.existence,
                is_latest=is_latest,
                public=event_v.public,
                name=event_v.name,
                user_id=user.user_id,
                user_name=user.name,
                user_moderator=user.moderator,
                gravatar_hash=user.auth.gravatar_hash,
                url=event_v.url,
                url_v=event_v.url_v,
                )
            history.append(entity)

        if not history:
            raise HTTPError(404, "%s: No such event" % (event_id_string))

        if not self.moderator:
            if len(history) == int(bool(event)):
                raise HTTPError(404)
        
        version_current_url = (event and event.url) or (not self.moderator and history and history[-1].url)

        self.render(
            'revision-history.html',
            entity=True,
            version_current_url=version_current_url,
            latest_a_time=event and event.a_time,
            title_text="Revision History",
            history=history,
            )
        


class EventRevisionHandler(BaseEventHandler):
    def _get_event_revision(self, event_id_string, event_v_id_string):
        event_id = int(event_id_string)
        event_v_id = int(event_v_id_string)

        query = self.orm.query(Event_v) \
            .filter_by(event_id=event_id) \
            .filter_by(event_v_id=event_v_id)

        try:
            event_v = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d:%d: No such event revision" % (event_id, event_v_id))

        query = self.orm.query(Event) \
            .filter_by(event_id=event_id)

        try:
            event = query.one()
        except NoResultFound:
            event = None

        return event_v, event

    @authenticated
    def get(self, event_id_string, event_v_id_string):
        event_v, event = self._get_event_revision(event_id_string, event_v_id_string)

        if not event_v.existence:
            raise HTTPError(404)

        if self.moderator:
            if event and event.a_time == event_v.a_time:
                self.next = event.url
                return self.redirect_next()
        else:
            if not ((event_v.moderation_user == self.current_user) or \
                        (event and event_v.a_time == event.a_time)):
                raise HTTPError(404)
            newest_event_v = self.orm.query(Event_v) \
                .filter_by(moderation_user=self.current_user) \
                .order_by(Event_v.event_v_id.desc()) \
                .first()
            if not newest_event_v:
                raise HTTPError(404)
            latest_a_time = self._get_event_latest_a_time(event_id_string)
            if latest_a_time and event_v.a_time < latest_a_time:
                raise HTTPError(404)
            if event and newest_event_v.a_time < event.a_time:
                raise HTTPError(404)
            if newest_event_v == event_v:
                self.next = event_v.url
                return self.redirect_next()
            event = newest_event_v

        obj = event and event.obj(
            public=True,
            )

        obj_v = event_v.obj(
            public=True,
            )

        ignore_list = []
        fields = (
            ("name", "name"),
            ("start_date", "date"),
            ("end_date", "date"),
            ("description", "markdown"),
            ("start_time", "time"),
            ("end_time", "time"),
            ("public", "public")
            )

        if not self.moderator or not event_v.moderation_user.moderator:
            ignore_list.append(
                "public"
                )

        latest_a_time = self._get_event_latest_a_time(event_id_string)

        self.render(
            'revision.html',
            action_url=event_v.url,
            version_url="%s/revision" % (event_v.url),
            version_current_url=event and event.url,
            latest_a_time=latest_a_time,
            fields=fields,
            ignore_list=ignore_list,
            obj=obj,
            obj_v=obj_v,
            )
        


class EventAddressListHandler(BaseEventHandler, BaseAddressHandler):
    @authenticated
    def get(self, event_id_string):
        required = True
        if self.contributor:
            event_v = self._get_event_v(event_id_string)
            if event_v:
                required = False
        event = self._get_event(event_id_string, required=required)

        if not self.moderator and event_v:
            event = event_v

        obj = event.obj(
            public=self.moderator,
            )

        self.render(
            'address.html',
            address=None,
            entity=obj,
            entity_list="event_list",
            )
        
    @authenticated
    def post(self, event_id_string):
        required = True
        if self.contributor:
            event_v = self._get_event_v(event_id_string)
            if event_v:
                required = False
        event = self._get_event(event_id_string, required=required)

        address = self._create_address()
        self._before_address_set(address)
        self.orm.add(address)
        self.orm_commit()
        if self.moderator:
            event.address_list.append(address)
            self.orm_commit()
            return self.redirect_next(event.url)

        id_ = address.address_id

        self.orm.delete(address)
        self.orm_commit()

        self.orm.query(Address_v) \
            .filter(Address_v.address_id==id_) \
            .delete()
        self.orm_commit()

        address_v = self._create_address_v(id_)
        self.orm.add(address_v)
        self.orm_commit()

        event_id = event and event.event_id or event_v.event_id
        address_id = id_

        engine = self.orm.connection().engine
        sql = """
insert into event_address_v (event_id, address_id, a_time, existence)
values (%d, %d, 0, 1)""" % (event_id, address_id)
        engine.execute(sql)

        return self.redirect_next(address_v.url)



class EventAddressHandler(BaseEventHandler, BaseAddressHandler):
    @authenticated
    def put(self, event_id_string, address_id_string):
        event = self._get_event(event_id_string)
        address = self._get_address(address_id_string)
        if address not in event.address_list:
            event.address_list.append(address)
            self.orm_commit()
        return self.redirect_next(event.url)

    @authenticated
    def delete(self, event_id_string, address_id_string):
        if not self.moderator:
            raise HTTPError(405)

        event = self._get_event(event_id_string)
        address = self._get_address(address_id_string)
        if address in event.address_list:
            event.address_list.remove(address)
            self.orm_commit()
        return self.redirect_next(event.url)



class EventNoteListHandler(BaseEventHandler, BaseNoteHandler):
    @authenticated
    def post(self, event_id_string):
        if not self.moderator:
            raise HTTPError(404)

        event = self._get_event(event_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)
        
        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        event.note_list.append(note)
        self.orm_commit()
        return self.redirect_next(event.url)

    @authenticated
    def get(self, event_id_string):
        if not self.moderator:
            raise HTTPError(404)

        event = self._get_event(event_id_string)
        obj = event.obj(
            public=self.moderator,
            )
        self.next = event.url
        self.render(
            'note.html',
            entity=obj,
            )



class EventNoteHandler(BaseEventHandler, BaseNoteHandler):
    @authenticated
    def put(self, event_id_string, note_id_string):
        if not self.moderator:
            raise HTTPError(404)

        event = self._get_event(event_id_string)
        note = self._get_note(note_id_string)
        if note not in event.note_list:
            event.note_list.append(note)
            self.orm_commit()
        return self.redirect_next(event.url)

    @authenticated
    def delete(self, event_id_string, note_id_string):
        if not self.moderator:
            raise HTTPError(405)

        event = self._get_event(event_id_string)
        note = self._get_note(note_id_string)
        if note in event.note_list:
            event.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(event.url)



class EventEventtagListHandler(BaseEventHandler, BaseEventtagHandler):
    @authenticated
    def get(self, event_id_string):
        if not self.moderator:
            raise HTTPError(404)

        # event...

        event = self._get_event(event_id_string)

        if self.deep_visible():
            eventtag_list=event.eventtag_list
        else:
            eventtag_list=event.eventtag_list_public

        public = self.moderator

        eventtag_list = [eventtag.obj(public=public) for eventtag in eventtag_list]

        obj = event.obj(
            public=public,
            eventtag_obj_list=eventtag_list,
            )

        # eventtag...

        (eventtag_list, name, name_short, base, base_short, path, search) = \
            self._get_tag_search_args("event_len")

        self.render(
            'entity_tag.html',
            obj=obj,
            tag_list=eventtag_list,
            path=path,
            search=search,
            type_title="Event",
            type_title_plural="Events",
            type_url="event",
            type_tag_list="eventtag_list",
            type_entity_list="event_list",
            type_li_template="event_li",
            type_length="event_len",
            )



class EventEventtagHandler(BaseEventHandler, BaseEventtagHandler):
    @authenticated
    def put(self, event_id_string, eventtag_id_string):
        if not self.moderator:
            raise HTTPError(405)

        event = self._get_event(event_id_string)
        eventtag = self._get_eventtag(eventtag_id_string)
        if eventtag not in event.eventtag_list:
            event.eventtag_list.append(eventtag)
            self.orm_commit()
        return self.redirect_next(event.url)

    @authenticated
    def delete(self, event_id_string, eventtag_id_string):
        if not self.moderator:
            raise HTTPError(405)

        event = self._get_event(event_id_string)
        eventtag = self._get_eventtag(eventtag_id_string)
        if eventtag in event.eventtag_list:
            event.eventtag_list.remove(eventtag)
            self.orm_commit()
        return self.redirect_next(event.url)



class EventOrgListHandler(BaseEventHandler, BaseOrgHandler):
    @authenticated
    def get(self, event_id_string):
        if not self.moderator:
            raise HTTPError(404)
            
        is_json = self.content_type("application/json")

        # event...

        event = self._get_event(event_id_string)

        if self.deep_visible():
            org_list=event.org_list
        else:
            org_list=event.org_list_public
            
        public = self.moderator

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
            visibility=self.parameters.get("visibility", None),
            )

        org_list = []
        org_count = org_alias_name_query.count()
        for org, alias in org_alias_name_query[:20]:
            org_list.append(org.obj(
                    public=public,
                    alias=alias and alias.obj(
                        public=public,
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
        if not self.moderator:
            raise HTTPError(404)
            
        event = self._get_event(event_id_string)
        org = self._get_org(org_id_string)
        if org not in event.org_list:
            event.org_list.append(org)
            self.orm_commit()
        return self.redirect_next(event.url)

    @authenticated
    def delete(self, event_id_string, org_id_string):
        if not self.moderator:
            raise HTTPError(404)
            
        event = self._get_event(event_id_string)
        org = self._get_org(org_id_string)
        if org in event.org_list:
            event.org_list.remove(org)
            self.orm_commit()
        return self.redirect_next(event.url)



class EventDuplicateHandler(BaseEventHandler):
    @authenticated
    def post(self, event_id_string):
        if not self.moderator:
            raise HTTPError(404)
            
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
            moderation_user=self.current_user,
            public=public
            )
        self.orm.add(event2)

        for address in event.address_list:
            address2 = Address(
                address.postal,
                address.source,
                address.lookup,
                manual_longitude=address.manual_longitude,
                manual_latitude=address.manual_latitude,
                moderation_user=self.current_user,
                public=address.public
                )
            address2.geocode()
            event2.address_list.append(address2)

        for eventtag in event.eventtag_list:
            event2.eventtag_list.append(eventtag)

        for note in event.note_list:
            note2 = Note(
                note.text,
                note.source,
                moderation_user=self.current_user,
                public=note.public
                )
            event2.note_list.append(note2)

        for org in event.org_list:
            event2.org_list.append(org)

        self.orm_commit()
        return self.redirect_next(event2.url)
