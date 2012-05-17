# -*- coding: utf-8 -*-

from base import BaseHandler, authenticated

from model import Note


class BaseNoteHandler(BaseHandler):
    def _get_arguments(self):
        if self.content_type("application/x-www-form-urlencoded"):
            text = self.get_argument("text")
            source = self.get_argument("source")
        elif self.content_type("application/json"):
            text = self.get_json_argument("text")
            source = self.get_json_argument("source")
        else:
            raise tornado.web.HTTPError(400, "'content-type' required.")
        return text, source



class NoteListHandler(BaseNoteHandler):
    def get(self):

        note_list = Note.query_latest(self.orm).all()

        self.render(
            'note_list.html',
            current_user=self.current_user,
            uri=self.request.uri,
            note_list=note_list,
            xsrf=self.xsrf_token
            )

    def post(self):
        text, source = BaseNoteHandler._get_arguments(self)
        note = Note(text, source, moderation_user=self.current_user)
        self.orm.add(note)
        self.orm.commit()
        # Setting note_e in a trigger, so we have to update manually.
        self.orm.refresh(note)
        self.redirect(note.url)



class NoteHandler(BaseNoteHandler):
    def get(self, note_e_string, note_id_string):
        note_e = int(note_e_string)
        note_id = note_id_string and int(note_id_string) or None
        
        if note_id:
            if not self.current_user:
                return self.error(404, "Not found")
            query = self.orm.query(Note).filter_by(note_e=note_e).filter_by(note_id=note_id)
            error = "%d, %d: No such note, version" % (note_e, note_id)
        else:
            query = Note.query_latest(self.orm).filter_by(note_e=note_e)
            error = "%d: No such note" % note_e

        try:
            note = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, error)

        if self.accept_type("json"):
            self.write_json(note.obj())
        else:
            self.render(
                'note.html',
                current_user=self.current_user,
                uri=self.request.uri,
                xsrf=self.xsrf_token,
                note=note
                )

    @authenticated
    def put(self, note_e_string, note_id_string):
        if note_id_string:
            return self.error(405, "Cannot edit revisions.")

        note_e = int(note_e_string)

        query = Note.query_latest(self.orm).filter_by(note_e=note_e)

        try:
            note = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return self.error(404, "%d: No such note" % note_e)

        text, source = BaseNoteHandler._get_arguments(self)

        new_note = note.copy(moderation_user=self.current_user)
        new_note.text = text
        new_note.source = source
        self.orm.commit()
        self.redirect(new_note.url)
