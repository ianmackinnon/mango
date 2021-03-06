
from tornado.web import HTTPError

from model import Event, Eventtag, event_eventtag

from handle.base import authenticated, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from handle.base_tag import BaseTagHandler
from handle.note import BaseNoteHandler



class BaseEventtagHandler(BaseTagHandler):
    Tag = Eventtag
    Entity = Event
    tag_id = "eventtag_id"
    entity_id = "event_id"
    tag_type = "eventtag"
    entity_type = "event"
    cross_table = event_eventtag

    def _get_full_eventtag_list(self):
        eventtag_and_event_count_list = \
            self._get_eventtag_and_event_count_list_search(
                visibility=self.parameters.get("visibility", None),
            )
        eventtag_list = []
        for eventtag, event_count in eventtag_and_event_count_list:
            eventtag_list.append(eventtag.obj(
                public=self.moderator,
                event_len=event_count,
            ))
        return eventtag_list



class EventtagListHandler(BaseEventtagHandler,
                          MangoEntityListHandlerMixin):
    @property
    def _create(self):
        return self._create_tag

    @property
    def _get(self):
        return self._get_tag

    @authenticated
    def post(self):
        if not self.moderator:
            raise HTTPError(404)

        return MangoEntityListHandlerMixin.post(self)

    def get(self):
        (eventtag_list, _name, _name_short, _base, _base_short,
         path, search, sort) = self._get_tag_search_args()

        if self.accept_type("json"):
            self.write_json(eventtag_list)
        else:
            self.render(
                'tag-list.html',
                tag_list=eventtag_list,
                path=path,
                search=search,
                sort=sort,
                visibility=self.parameters.get("visibility", None),
                type_title="Event",
                type_title_plural="Events",
                type_url="event",
                type_entity_list="eventList",
                type_li_template="event_li",
                type_length="event_len",
                )



class EventtagNewHandler(BaseEventtagHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        if self.parameters.get("view", None) != "edit":
            self.next_ = "/eventtag"
            self.redirect_next()
            return

        path_list = self._get_path_list()
        self.render(
            'tag.html',
            type_title="Event",
            type_title_plural="Events",
            type_url="event",
            type_entity_list="eventList",
            type_li_template="event_li",
            path_list=path_list,
            )



class EventtagHandler(BaseEventtagHandler,
                      MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_tag

    @property
    def _get(self):
        return self._get_tag

    def _before_delete(self, eventtag):
        if eventtag.event_list:
            raise HTTPError(
                405, "Cannot delete tag because it has attached events.")

    @authenticated
    def put(self, entity_id):
        # pylint: disable=not-callable
        # `self._get` and `self._create` are properties

        if not self.moderator:
            raise HTTPError(404)

        old_entity = self._get(entity_id)
        new_entity = self._create(entity_id)

        if not old_entity.content_same(new_entity):
            if old_entity.is_virtual is not None:
                if old_entity.name != new_entity.name:
                    raise HTTPError(
                        404, "May not change the name of a virtual tag.")
            old_entity.content_copy(new_entity, self.current_user)
            self.orm_commit()

        return self.redirect_next(old_entity.url)

    def get(self, eventtag_id):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_offset = self.get_argument_int("note_offset", None)

        public = self.moderator

        eventtag = self._get_tag(eventtag_id)

        event_list_query = self.orm.query(Event) \
            .join(event_eventtag) \
            .filter(
                Event.event_id == event_eventtag.c.event_id,
                event_eventtag.c.eventtag_id == eventtag.eventtag_id,
            )
        event_list_query = self.filter_visibility(
            event_list_query,
            Event,
            visibility=self.parameters.get("visibility", None),
            )
        event_list = event_list_query \
            .order_by(Event.start_date.desc()) \
            .all()

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
            event_list=event_list,
            note_list=note_list,
            note_count=note_count,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            path_list = self._get_path_list()
            self.render(
                'tag.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                type_title="Event",
                type_title_plural="Events",
                type_url="event",
                type_entity_list="eventList",
                type_li_template="event_li",
                path_list=path_list,
                )



class EventtagNoteListHandler(BaseEventtagHandler, BaseNoteHandler):
    @authenticated
    def post(self, eventtag_id):
        if not self.moderator:
            raise HTTPError(404)

        eventtag = self._get_tag(eventtag_id)
        note = self._create_note()
        eventtag.note_list.append(note)
        self.orm_commit()
        return self.redirect_next(eventtag.url)

    @authenticated
    def get(self, eventtag_id):
        if not self.moderator:
            raise HTTPError(404)

        eventtag = self._get_tag(eventtag_id)

        obj = eventtag.obj(
            public=self.moderator,
            )
        self.next_ = eventtag.url
        self.render(
            'note.html',
            entity=obj
            )



class EventtagNoteHandler(BaseEventtagHandler, BaseNoteHandler):
    @authenticated
    def put(self, eventtag_id, note_id):
        if not self.moderator:
            raise HTTPError(404)

        eventtag = self._get_tag(eventtag_id)
        note = self._get_note(note_id)
        if note not in eventtag.note_list:
            eventtag.note_list.append(note)
            self.orm_commit()
        return self.redirect_next(eventtag.url)

    @authenticated
    def delete(self, eventtag_id, note_id):
        if not self.moderator:
            raise HTTPError(404)

        eventtag = self._get_tag(eventtag_id)
        note = self._get_note(note_id)
        if note in eventtag.note_list:
            eventtag.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(eventtag.url)
