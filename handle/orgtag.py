# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from tornado.web import HTTPError

from base import authenticated, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from base_tag import BaseTagHandler
from note import BaseNoteHandler

from model import Org, Orgtag, Note, org_orgtag



class BaseOrgtagHandler(BaseTagHandler):
    Tag = Orgtag
    Entity = Org
    tag_id = "orgtag_id"
    entity_id = "org_id"
    cross_table = org_orgtag
    tag_type = "orgtag"

    def _get_full_orgtag_list(self):
        orgtag_and_org_count_list = \
            self._get_orgtag_and_org_count_list_search(
            visibility=self.parameters.get("visibility", None),
            )
        orgtag_list = []
        for orgtag, org_count in orgtag_and_org_count_list:
            orgtag_list.append(orgtag.obj(
                    public=self.moderator,
                    org_len=org_count,
                    ))
        return orgtag_list



class OrgtagListHandler(BaseOrgtagHandler,
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
            raise HTTPError(405)
        
        return MangoEntityListHandlerMixin.post(self)
        
    def get(self):
        (orgtag_list, name, name_short, base, base_short, path, search) = \
            self._get_tag_search_args("org_len")

        if self.accept_type("json"):
            self.write_json(orgtag_list)
        else:
            self.render(
                'tag_list.html',
                tag_list=orgtag_list,
                path=path,
                search=search,
                visibility=self.parameters.get("visibility", None),
                type_title="Company",
                type_title_plural="Companies",
                type_url="organisation",
                type_entity_list="org_list",
                type_li_template="org_li",
                type_length="org_len",
                )



class OrgtagNewHandler(BaseOrgtagHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        path_list = self._get_path_list()
        self.render(
            'tag.html',
            type_title="Company",
            type_title_plural="Companies",
            type_url="organisation",
            type_entity_list="org_list",
            type_li_template="org_li",
            path_list=path_list,
            )



class OrgtagHandler(BaseOrgtagHandler,
                    MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_tag

    @property
    def _get(self):
        return self._get_tag

    def _before_delete(self, orgtag):
        if orgtag.org_list:
            raise HTTPError(405, "Cannot delete tag because it has attached organisations.")

    @authenticated
    def put(self, entity_id):
        if not self.moderator:
            raise HTTPError(405)

        old_entity = self._get(entity_id)
        new_entity = self._create(entity_id)

        if not old_entity.content_same(new_entity):
            old_entity.content_copy(new_entity, self.current_user)
            self.orm_commit()
        
        return self.redirect_next(old_entity.url)
        
    def get(self, orgtag_id):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_offset = self.get_argument_int("note_offset", None)

        public = self.moderator

        orgtag = self._get_tag(orgtag_id)

        org_list_query = self.orm.query(Org) \
            .join(org_orgtag) \
            .filter(Org.org_id==org_orgtag.c.org_id) \
            .filter(org_orgtag.c.orgtag_id==orgtag.orgtag_id)
        org_list_query = self.filter_visibility(
            org_list_query,
            Org,
            visibility=self.parameters.get("visibility", None),
            )
        org_list = org_list_query.all()

        note_list, note_count = orgtag.note_list_filtered(
            note_search=note_search,
            note_order=note_order,
            note_offset=note_offset,
            all_visible=self.deep_visible()
            )

        org_list = [org.obj(public=public) for org in org_list]
        note_list = [note.obj(public=public) for note in note_list]

        obj = orgtag.obj(
            public=public,
            org_list=org_list,
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
                type_title="Company",
                type_title_plural="Companies",
                type_url="organisation",
                type_entity_list="org_list",
                type_li_template="org_li",
                path_list=path_list,
                )



class OrgtagNoteListHandler(BaseOrgtagHandler, BaseNoteHandler):
    @authenticated
    def post(self, orgtag_id):
        if not self.moderator:
            raise HTTPError(405)

        orgtag = self._get_tag(orgtag_id)
        note = self._create_note()
        orgtag.note_list.append(note)
        self.orm_commit()
        return self.redirect_next(orgtag.url)

    @authenticated
    def get(self, orgtag_id): 
        orgtag = self._get_tag(orgtag_id)

        obj = orgtag.obj(
            public=self.moderator,
            )
        self.next = orgtag.url
        self.render(
            'note.html',
            entity=obj
            )



class OrgtagNoteHandler(BaseOrgtagHandler, BaseNoteHandler):
    @authenticated
    def put(self, orgtag_id, note_id):
        if not self.moderator:
            raise HTTPError(405)

        orgtag = self._get_tag(orgtag_id)
        note = self._get_note(note_id)
        if note not in orgtag.note_list:
            orgtag.note_list.append(note)
            self.orm_commit()
        return self.redirect_next(orgtag.url)

    @authenticated
    def delete(self, orgtag_id, note_id):
        if not self.moderator:
            raise HTTPError(405)

        orgtag = self._get_tag(orgtag_id)
        note = self._get_note(note_id)
        if note in orgtag.note_list:
            orgtag.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(orgtag.url)



