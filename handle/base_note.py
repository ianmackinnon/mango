# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound
from tornado.web import HTTPError

from base import BaseHandler, MangoBaseEntityHandlerMixin

from model import User, Note, note_fts, detach

from model_v import Note_v



class BaseNoteHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    def _get_note(self, note_id, required=True):
        return self._get_entity(Note, "note_id",
                                "note",
                                note_id,
                                required,
                                )
    
    def _get_note_v(self, note_v_id):
        return self._get_entity_v(Note, "note_id",
                                  Note_v, "note_v_id",
                                  "note",
                                  note_v_id,
                                  )

    def _create_note(self, id_=None, version=False):
        is_json = self.content_type("application/json")

        text = self.get_argument("text", json=is_json)
        source = self.get_argument("source", json=is_json)

        public, moderation_user = self._create_revision()

        if version:
            note = Note_v(
                id_,
                text, source,
                moderation_user=moderation_user, public=public)
        else:
            note = Note(
                text, source,
                moderation_user=moderation_user, public=public)
            
            if id_:
                note.note_id = id_

        detach(note)
        
        return note
    
    def _note_history_query(self, note_id):
        return self._history_query(
            Note, "note_id",
            Note_v,
            note_id)
    
    def _get_note_history(self, note_id):
        note_v_query, note = self._note_history_query(note_id)
        
        note_v_query = note_v_query \
            .order_by(Note_v.note_v_id.desc())
        
        return note_v_query.all(), note
    
    def _count_note_history(self, note_id):
        note_v_query, note = self._note_history_query(note_id)
        
        return note_v_query.count()
    
    def _get_note_latest_a_time(self, note_id):
        note_v = self.orm.query(Note_v.a_time) \
            .join((User, Note_v.moderation_user)) \
            .filter(Note_v.note_id == note_id) \
            .filter(User.moderator == True) \
            .order_by(Note_v.note_v_id.desc()) \
            .first()
        
        return note_v and note_v.a_time or None
    
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
        


