# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from tornado.web import HTTPError

from base import BaseHandler, authenticated, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from note import BaseNoteHandler

from model import Event, Eventtag, Note, event_eventtag, short_name, detach



class BaseEventtagHandler(BaseHandler): 
    def _get_eventtag(self, eventtag_id_string, options=None):
        eventtag_id = int(eventtag_id_string)

        query = self.orm.query(Eventtag)\
            .filter_by(eventtag_id=eventtag_id)

        if not self.current_user:
            query = query \
                .filter_by(public=True)

        if options:
            query = query \
                .options(*options)

        try:
            eventtag = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d: No such eventtag" % eventtag_id)

        return eventtag

    def _create_eventtag(self):
        name, public, note_id_list = BaseEventtagHandler._get_arguments(self)

        moderation_user = self.current_user

        eventtag = Eventtag(
            name,
            moderation_user=moderation_user, public=public,)

        detach(eventtag)

        return eventtag

    def _get_arguments(self):
        is_json = self.content_type("application/json")

        name = self.get_argument("name", json=is_json)
        public = self.get_argument_public("public", json=is_json)
        note_id_list = self.get_argument("note_id", [], json=is_json)

        return name, public, note_id_list

    def _get_eventtag_and_event_count_list_search(
        self, name=None, short=None, search=None, visibility=None):
        tag_list = self.orm.query(Eventtag)
        event_q = self.orm.query(Event)

        tag_list = self.filter_visibility(tag_list, Eventtag, visibility)
        event_q = self.filter_visibility(event_q, Event, visibility).subquery()

        if name:
            tag_list = tag_list.filter_by(name=name)

        if short:
            tag_list = tag_list.filter_by(short=short)

        if search:
            search = short_name(search)
            tag_list = tag_list.filter(Eventtag.short.contains(search))

        s = self.orm.query(
            event_eventtag.c.eventtag_id, 
            func.count(event_eventtag.c.event_id).label("count")
            )\
            .join((event_q, event_q.c.event_id == event_eventtag.c.event_id))\
            .group_by(event_eventtag.c.eventtag_id)\
            .subquery()

        results = tag_list\
            .add_columns(s.c.count)\
            .outerjoin((s, Eventtag.eventtag_id == s.c.eventtag_id))

        if search:
            results = results\
                .order_by(Eventtag.short.startswith(search).desc())

        results = results\
            .order_by(s.c.count.desc())\
            .all()

        tag_and_event_count_list = results

        return tag_and_event_count_list
        
    def _get_eventtag_and_event_count_list_search_and_args(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        short = self.get_argument("short", None, json=is_json)
        search = self.get_argument("search", None, json=is_json)

        eventtag_and_event_count_list = self._get_eventtag_and_event_count_list_search(
            name=name,
            short=short,
            search=search,
            visibility=self.parameters["visibility"],
            )

        return eventtag_and_event_count_list, name, short, search

    def _get_full_eventtag_list(self):
        eventtag_and_event_count_list = \
            self._get_eventtag_and_event_count_list_search(
            visibility=self.parameters["visibility"],
            )
        eventtag_list = []
        for eventtag, event_count in eventtag_and_event_count_list:
            eventtag_list.append(eventtag.obj(
                    public=bool(self.current_user),
                    event_len=event_count,
                    ))
        return eventtag_list



class EventtagListHandler(BaseEventtagHandler,
                          MangoEntityListHandlerMixin):
    @property
    def _create(self):
        return self._create_eventtag

    @property
    def _get(self):
        return self._get_eventtag

    def get(self):
        eventtag_and_event_count_list, name, short, search = \
            BaseEventtagHandler._get_eventtag_and_event_count_list_search_and_args(self)

        eventtag_list = []
        for eventtag, event_count in eventtag_and_event_count_list:
            eventtag_list.append(eventtag.obj(
                    public=bool(self.current_user),
                    event_len=event_count,
                    ))

        if self.accept_type("json"):
            self.write_json(eventtag_list)
        else:
            self.render(
                'tag_list.html',
                tag_list=eventtag_list,
                search=search,
                visibility=self.parameters["visibility"],
                type_title="Event",
                type_title_plural="Events",
                type_url="event",
                type_entity_list="event_list",
                type_li_template="event_li",
                )



class EventtagNewHandler(BaseEventtagHandler):
    @authenticated
    def get(self):
        self.render(
            'tag.html',
            type_title="Event",
            type_title_plural="Events",
            type_url="event",
            type_entity_list="event_list",
            type_li_template="event_li",
            )



class EventtagHandler(BaseEventtagHandler,
                      MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_eventtag

    @property
    def _get(self):
        return self._get_eventtag

    def _before_delete(self, eventtag):
        if eventtag.event_list:
            raise HTTPError(405, "Cannot delete tag because it has attached events.")

    def get(self, eventtag_id_string):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_offset = self.get_argument_int("note_offset", None)

        public = bool(self.current_user)

        eventtag = self._get_eventtag(eventtag_id_string)

        event_list_query = self.orm.query(Event) \
            .join(event_eventtag) \
            .filter(Event.event_id==event_eventtag.c.event_id) \
            .filter(event_eventtag.c.eventtag_id==eventtag.eventtag_id)
        event_list_query = self.filter_visibility(
            event_list_query,
            Event,
            visibility=self.parameters["visibility"],
            )
        event_list = event_list_query.all()

        note_list, note_count = eventtag.note_list_filtered(
            note_search=note_search,
            note_order=note_order,
            note_offset=note_offset,
            all_visible=self.deep_visible(),
            )

        event_list = [event.obj(public=public) for event in event_list]
        note_list = [note.obj(public=public) for note in note_list]

        obj = eventtag.obj(
            public=public,
            event_obj_list=event_list,
            note_obj_list=note_list,
            note_count=note_count,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'tag.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                type_title="Event",
                type_title_plural="Events",
                type_url="event",
                type_entity_list="event_list",
                type_li_template="event_li",
                )



class EventtagNoteListHandler(BaseEventtagHandler, BaseNoteHandler):
    @authenticated
    def post(self, eventtag_id_string):
        eventtag = self._get_eventtag(eventtag_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)

        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        eventtag.note_list.append(note)
        self.orm.commit()
        self.redirect(eventtag.url)

    @authenticated
    def get(self, eventtag_id_string): 
        public = bool(self.current_user)

        eventtag = self._get_eventtag(eventtag_id_string)

        obj = eventtag.obj(
            public=public,
            )
        self.next = eventtag.url
        self.render(
            'note.html',
            entity=obj
            )



class EventtagNoteHandler(BaseEventtagHandler, BaseNoteHandler):
    @authenticated
    def put(self, eventtag_id_string, note_id_string):
        eventtag = self._get_eventtag(eventtag_id_string)
        note = self._get_note(note_id_string)
        if note not in eventtag.note_list:
            eventtag.note_list.append(note)
            self.orm.commit()
        self.redirect(eventtag.url)

    @authenticated
    def delete(self, eventtag_id_string, note_id_string):
        eventtag = self._get_eventtag(eventtag_id_string)
        note = self._get_note(note_id_string)
        if note in eventtag.note_list:
            eventtag.note_list.remove(note)
            self.orm.commit()
        self.redirect(eventtag.url)



