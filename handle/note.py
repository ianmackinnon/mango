# -*- coding: utf-8 -*-

from tornado.web import HTTPError

from base import authenticated, \
    HistoryEntity, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from base_note import BaseNoteHandler

from model import Note

from model_v import Note_v



class NoteListHandler(BaseNoteHandler,
                      MangoEntityListHandlerMixin):
    Entity = Note
    Entity_v = Note_v
    entity_id = "note_id"
    entity_v_id = "note_v_id"

    @property
    def _create(self):
        return self._create_note

    @property
    def _get(self):
        return self._get_note

    @authenticated
    def post(self):
        if not self.moderator:
            raise HTTPError(405)
        return MangoEntityListHandlerMixin.post(self);

    def get(self):
        note_list = self.orm.query(Note)

        note_list = self.filter_visibility(
            note_list, Note, self.parameters.get("visibility", None))

        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_list = self._filter_search(note_list, note_search, note_order)

        note_list = [note.obj(public=self.moderator) \
                         for note in note_list.limit(20)]

        self.render(
            'note_list.html',
            note_list=note_list,
            note_search=note_search,
            note_order=note_order,
            )



class NoteNewHandler(BaseNoteHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)
        self.render('note.html')



class NoteHandler(BaseNoteHandler, MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_note

    @property
    def _get(self):
        return self._get_note

    @authenticated
    def put(self, entity_id_string):
        if not self.moderator:
            raise HTTPError(405)
        return MangoEntityHandlerMixin.put(self, entity_id_string);

    @authenticated
    def touch(self, entity_id_string):
        if not self.moderator:
            raise HTTPError(405)
        return MangoEntityHandlerMixin.touch(self, entity_id_string);

    @authenticated
    def delete(self, entity_id_string):
        if not self.moderator:
            raise HTTPError(405)
        return MangoEntityHandlerMixin.delete(self, entity_id_string);

    def get(self, note_id_string):
        public = self.moderator

        required = True
        if self.moderator:
            note_v = self._get_note_v(note_id_string)
            if note_v:
                required = False
        note = self._get_note(note_id_string, required=required)

        if not note:
            self.next = "%s/revision" % note_v.url
            return self.redirect_next()

        if self.deep_visible():
            address_list=note.address_list
            orgtag_list=note.orgtag_list
            org_list=note.org_list
        else:
            address_list=note.address_list_public
            orgtag_list=note.orgtag_list_public
            org_list=note.org_list_public

        address_list = [address.obj(public=public) for address in address_list]
        orgtag_list = [orgtag.obj(public=public) for orgtag in orgtag_list]
        org_list = [org.obj(public=public) for org in org_list]

        obj = note.obj(
            public=public,
            address_obj_list=address_list,
            orgtag_obj_list=orgtag_list,
            org_obj_list=org_list,
            )

        version_url=None
        if self.moderator and self._count_note_history(note_id_string) > 1:
            version_url="%s/revision" % note.url

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'note.html',
                obj=obj,
                version_url=version_url,
                )



class NoteRevisionListHandler(BaseNoteHandler):
    @authenticated
    def get(self, note_id_string):
        if not self.moderator:
            raise HTTPError(404)

        note_v_list, note = self._get_note_history(note_id_string)

        history = []
        for note_v in note_v_list:
            user = note_v.moderation_user

            is_latest = False
            if self.moderator:
                if note and note.a_time == note_v.a_time:
                    is_latest = True
            else:
                if not history:
                    is_latest = True

            entity = HistoryEntity(
                type="note",
                entity_id=note_v.note_id,
                entity_v_id=note_v.note_v_id,
                date=note_v.a_time,
                existence=bool(note),
                existence_v=note_v.existence,
                is_latest=is_latest,
                public=note_v.public,
                name=note_v.text,
                user_id=user.user_id,
                user_name=user.name,
                user_moderator=user.moderator,
                gravatar_hash=user.auth.gravatar_hash,
                url=note_v.url,
                url_v=note_v.url_v,
                )
            history.append(entity)

        if not history:
            raise HTTPError(404, "%s: No such note" % (note_id_string))

        if not self.moderator:
            if len(history) == int(bool(note)):
                raise HTTPError(404)
        
        version_current_url = (note and note.url) or (not self.moderator and history and history[-1].url)

        self.render(
            'revision-history.html',
            entity=True,
            version_current_url=version_current_url,
            latest_a_time=note and note.a_time,
            title_text="Revision History",
            history=history,
            )
        


class NoteRevisionHandler(BaseNoteHandler):
    def _get_note_revision(self, note_id_string, note_v_id_string):
        note_id = int(note_id_string)
        note_v_id = int(note_v_id_string)

        query = self.orm.query(Note_v) \
            .filter_by(note_id=note_id) \
            .filter_by(note_v_id=note_v_id)

        try:
            note_v = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d:%d: No such note revision" % (note_id, note_v_id))

        query = self.orm.query(Note) \
            .filter_by(note_id=note_id)

        try:
            note = query.one()
        except NoResultFound:
            note = None

        return note_v, note

    @authenticated
    def get(self, note_id_string, note_v_id_string):
        if not self.moderator:
            raise HTTPError(404)

        note_v, note = self._get_note_revision(note_id_string, note_v_id_string)

        if not note_v.existence:
            raise HTTPError(404)

        if self.moderator:
            if note and note.a_time == note_v.a_time:
                self.next = note.url
                return self.redirect_next()
        else:
            if not ((note_v.moderation_user == self.current_user) or \
                        (note and note_v.a_time == note.a_time)):
                raise HTTPError(404)
            newest_note_v = self.orm.query(Note_v) \
                .filter_by(moderation_user=self.current_user) \
                .order_by(Note_v.note_v_id.desc()) \
                .first()
            if not newest_note_v:
                raise HTTPError(404)
            latest_a_time = self._get_note_latest_a_time(note_id_string)
            if latest_a_time and note_v.a_time < latest_a_time:
                raise HTTPError(404)
            if note and newest_note_v.a_time < note.a_time:
                raise HTTPError(404)
            if newest_note_v == note_v:
                self.next = note_v.url
                return self.redirect_next()
            note = newest_note_v

        obj = note and note.obj(
            public=True,
            )

        obj_v = note_v.obj(
            public=True,
            )

        ignore_list = []
        fields = (
            ("text", "markdown"),
            ("source", "markdown"),
            ("public", "public")
            )

        if not self.moderator or not note_v.moderation_user.moderator:
            ignore_list.append(
                "public"
                )

        latest_a_time = self._get_note_latest_a_time(note_id_string)

        self.render(
            'revision.html',
            action_url=note_v.url,
            version_url="%s/revision" % (note_v.url),
            version_current_url=note and note.url,
            latest_a_time=latest_a_time,
            fields=fields,
            ignore_list=ignore_list,
            obj=obj,
            obj_v=obj_v,
            )
        


