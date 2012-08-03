# -*- coding: utf-8 -*-

from sqlalchemy.orm import joinedload

from base import authenticated
from base_note import BaseNoteHandler
from orgtag import BaseOrgtagHandler
from org import BaseOrgHandler
from model import Note



class NoteListHandler(BaseNoteHandler):
    def get(self):
        note_list = self.orm.query(Note)

        note_list = self.filter_visibility(
            note_list, Note, self.parameters["visibility"])

        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_list = self._filter_search(note_list, note_search, note_order)

        note_list = [note.obj(public=bool(self.current_user)) \
                         for note in note_list.limit(20)]

        self.render(
            'note_list.html',
            note_list=note_list,
            note_search=note_search,
            note_order=note_order,
            )

    def post(self):
        text, source, public = BaseNoteHandler._get_arguments(self)
        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        self.orm.add(note)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + note.url)



class NoteLinkHandler(BaseNoteHandler, BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def get(self, note_id_string):
        orgtag_search = self.get_argument("orgtag_search", None)
        orgtag_list = self._get_orgtag_list_search(search=orgtag_search)

        org_search = self.get_argument("org_search", None)
        org_list, org_count, geobox, latlon = self._get_org_list_search(name_search=org_search)

        note = self._get_note(note_id_string)
        self.render(
            'note_link.html',
            note=note,
            orgtag_search=orgtag_search,
            orgtag_list=orgtag_list,
            org_search=org_search,
            org_list=org_list,
            org_count=org_count,
            )



class NoteNewHandler(BaseNoteHandler):
    def get(self):
        self.render('note.html')



class NoteHandler(BaseNoteHandler):
    def get(self, note_id_string):
        public = bool(self.current_user)

        if self.deep_visible():
            options = (
                joinedload("address_list"),
                joinedload("orgtag_list"),
                joinedload("org_list"),
                )
        else:
            options = (
                joinedload("address_list_public"),
                joinedload("orgtag_list_public"),
                joinedload("org_list_public"),
                )

        note = self._get_note(note_id_string, options=options)

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

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'note.html',
                obj=obj
                )

    @authenticated
    def delete(self, note_id_string):
        note = self._get_note(note_id_string)
        self.orm.delete(note)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + "/note")
        
    @authenticated
    def put(self, note_id_string):
        note = self._get_note(note_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)

        if note.text == text and \
                note.public == public and \
                note.source == source:
            self.redirect(self.next or self.url_root[:-1] + note.url)
            return

        note.text = text
        note.source = source
        note.public = public
        note.moderation_user = self.current_user
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + note.url)
