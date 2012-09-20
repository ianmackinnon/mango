# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from tornado.web import HTTPError

from base import BaseHandler, authenticated
from note import BaseNoteHandler

from model import Org, Orgtag, Note, org_orgtag, short_name



class BaseOrgtagHandler(BaseHandler): 
    def _get_orgtag(self, orgtag_id_string, options=None):
        orgtag_id = int(orgtag_id_string)

        query = self.orm.query(Orgtag)\
            .filter_by(orgtag_id=orgtag_id)

        if not self.current_user:
            query = query \
                .filter_by(public=True)

        if options:
            query = query \
                .options(*options)

        try:
            orgtag = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d: No such orgtag" % orgtag_id)

        return orgtag

    def _get_arguments(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)
        public = self.get_argument_public("public", json=is_json)
        note_id_list = self.get_argument("note_id", [], json=is_json)

        return name, public, note_id_list

    def _get_orgtag_and_org_count_list_search(
        self, name=None, short=None, search=None, visibility=None):
        tag_list = self.orm.query(Orgtag)
        org_q = self.orm.query(Org)

        tag_list = self.filter_visibility(tag_list, Orgtag, visibility)
        org_q = self.filter_visibility(org_q, Org, visibility).subquery()

        if name:
            tag_list = tag_list.filter_by(name=name)

        if short:
            tag_list = tag_list.filter_by(short=short)

        if search:
            search = short_name(search)
            tag_list = tag_list.filter(Orgtag.short.contains(search))

        s = self.orm.query(
            org_orgtag.c.orgtag_id, 
            func.count(org_orgtag.c.org_id).label("count")
            )\
            .join((org_q, org_q.c.org_id == org_orgtag.c.org_id))\
            .group_by(org_orgtag.c.orgtag_id)\
            .subquery()

        results = tag_list\
            .add_columns(s.c.count)\
            .outerjoin((s, Orgtag.orgtag_id == s.c.orgtag_id))

        if search:
            results = results\
                .order_by(Orgtag.short.startswith(search).desc())

        results = results\
            .order_by(s.c.count.desc())\
            .all()

        tag_and_org_count_list = results

        return tag_and_org_count_list
        
    def _get_orgtag_and_org_count_list_search_and_args(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        short = self.get_argument("short", None, json=is_json)
        search = self.get_argument("search", None, json=is_json)

        orgtag_and_org_count_list = self._get_orgtag_and_org_count_list_search(
            name=name,
            short=short,
            search=search,
            visibility=self.parameters["visibility"],
            )

        return orgtag_and_org_count_list, name, short, search

    def _get_full_orgtag_list(self):
        orgtag_and_org_count_list = \
            self._get_orgtag_and_org_count_list_search(
            visibility=self.parameters["visibility"],
            )
        orgtag_list = []
        for orgtag, org_count in orgtag_and_org_count_list:
            orgtag_list.append(orgtag.obj(
                    public=bool(self.current_user),
                    org_len=org_count,
                    ))
        return orgtag_list



class OrgtagListHandler(BaseOrgtagHandler):
    def get(self):
        orgtag_and_org_count_list, name, short, search = \
            BaseOrgtagHandler._get_orgtag_and_org_count_list_search_and_args(self)

        orgtag_list = []
        for orgtag, org_count in orgtag_and_org_count_list:
            orgtag_list.append(orgtag.obj(
                    public=bool(self.current_user),
                    org_len=org_count,
                    ))

        if self.accept_type("json"):
            self.write_json(orgtag_list)
        else:
            self.render(
                'tag_list.html',
                tag_list=orgtag_list,
                search=search,
                visibility=self.parameters["visibility"],
                type_title="Organisation",
                type_title_plural="Organisations",
                type_url="organisation",
                type_entity_list="org_list",
                type_li_template="org_li",
                )

    def post(self):
        name, public, note_id_list = BaseOrgtagHandler._get_arguments(self)

        orgtag = Orgtag(name,
                         moderation_user=self.current_user,
                         public=public,
                         )
        self.orm.add(orgtag)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + orgtag.url)



class OrgtagNewHandler(BaseOrgtagHandler):
    def get(self):
        self.render(
            'tag.html',
            type_title="Organisation",
            type_title_plural="Organisations",
            type_url="organisation",
            type_entity_list="org_list",
            type_li_template="org_li",
            )



class OrgtagHandler(BaseOrgtagHandler):
    def get(self, orgtag_id_string):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)

        public = bool(self.current_user)

        orgtag = self._get_orgtag(orgtag_id_string)

        if self.deep_visible():
            org_list=orgtag.org_list
            note_list=orgtag.note_list
        else:
            org_list=orgtag.org_list_public
            note_list=orgtag.note_list_public

        org_list = [org.obj(public=public) for org in org_list]
        note_list = [note.obj(public=public) for note in note_list]

        obj = orgtag.obj(
            public=public,
            org_obj_list=org_list,
            note_obj_list=note_list,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'tag.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                type_title="Organisation",
                type_title_plural="Organisations",
                type_url="organisation",
                type_entity_list="org_list",
                type_li_template="org_li",
                )

    @authenticated
    def delete(self, orgtag_id_string):
        orgtag = self._get_orgtag(orgtag_id_string)
        if orgtag.org_list:
            return self.error(405, "Method not allowed. Tag has attached Organisations.")
        self.orm.delete(orgtag)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + "/organisation")
        
    @authenticated
    def put(self, orgtag_id_string):
        orgtag = self._get_orgtag(orgtag_id_string)
        name, public, note_id_list = BaseOrgtagHandler._get_arguments(self)

        note_list = self.orm.query(Note)\
            .filter(Note.note_id.in_(note_id_list)).all()
        
        if orgtag.name == name and \
                orgtag.public == public and \
                orgtag.note_list == note_list:
            self.redirect(self.next or self.url_root[:-1] + orgtag.url)
            return
            
        orgtag.name = name
        orgtag.public = public
        orgtag.moderation_user = self.current_user
        orgtag.note_list = note_list
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + orgtag.url)


class OrgtagNoteListHandler(BaseOrgtagHandler, BaseNoteHandler):
    @authenticated
    def post(self, orgtag_id_string):
        orgtag = self._get_orgtag(orgtag_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)

        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        orgtag.note_list.append(note)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + orgtag.url)

    def get(self, orgtag_id_string): 
        public = bool(self.current_user)

        orgtag = self._get_orgtag(orgtag_id_string)

        obj = orgtag.obj(
            public=public,
            )
        self.next = orgtag.url
        self.render(
            'note.html',
            entity=obj
            )



class OrgtagNoteHandler(BaseOrgtagHandler, BaseNoteHandler):
    @authenticated
    def put(self, orgtag_id_string, note_id_string):
        orgtag = self._get_orgtag(orgtag_id_string)
        note = self._get_note(note_id_string)
        if note not in orgtag.note_list:
            orgtag.note_list.append(note)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + orgtag.url)

    @authenticated
    def delete(self, orgtag_id_string, note_id_string):
        orgtag = self._get_orgtag(orgtag_id_string)
        note = self._get_note(note_id_string)
        if note in orgtag.note_list:
            orgtag.note_list.remove(note)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + orgtag.url)



