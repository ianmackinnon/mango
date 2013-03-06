# -*- coding: utf-8 -*-

from base import authenticated
from base_note import BaseNoteHandler
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

    @authenticated
    def post(self):
        text, source, public = BaseNoteHandler._get_arguments(self)
        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        self.orm.add(note)
        self.orm.commit()
        self.redirect(note.url)



class NoteNewHandler(BaseNoteHandler):
    @authenticated
    def get(self):
        self.render('note.html')



class NoteHandler(BaseNoteHandler):
    def get(self, note_id_string):
        public = bool(self.current_user)

        note = self._get_note(note_id_string)

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
        self.redirect("/note")
        
    @authenticated
    def put(self, note_id_string):
        note = self._get_note(note_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)

        if note.text == text and \
                note.public == public and \
                note.source == source:
            self.redirect(note.url)
            return

        note.text = text
        note.source = source
        note.public = public
        note.moderation_user = self.current_user
        self.orm.commit()
        self.redirect(note.url)
