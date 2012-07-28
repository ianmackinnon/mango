# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound
from tornado.web import HTTPError

from base import BaseHandler
from model import Note, note_fts


class BaseNoteHandler(BaseHandler):
    def _get_note(self, note_id_string, options=None):
        note_id = int(note_id_string)

        query = self.orm.query(Note)\
            .filter_by(note_id=note_id)

        if options:
            query = query \
                .options(*options)

        if not self.current_user:
            query = query \
                .filter_by(public=True)

        try:
            note = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d: No such note" % note_id)

        return note

    def _get_arguments(self):
        is_json = self.content_type("application/json")
        text = self.get_argument("text", json=is_json)
        source = self.get_argument("source", json=is_json)
        public = self.get_argument_public("public", json=is_json)

        return text, source, public

    def _filter_search(self, query, note_search, note_order=None):
        if note_search:
            query = query \
                .join((note_fts, note_fts.c.docid == Note.note_id)) \
                .filter(note_fts.c.content.match(note_search))
        if note_order:
            query = query \
                .order_by({
                        "desc":Note.a_time.desc(),
                        "asc":Note.a_time.asc(),
                        }[note_order])
        else:
            query = query \
                .order_by(Note.a_time.desc())
        return query
        


