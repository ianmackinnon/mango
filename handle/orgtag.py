# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from tornado.web import HTTPError

from base import authenticated, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from base_tag import BaseTagHandler
from note import BaseNoteHandler

from model import Org, Orgtag, Note, org_orgtag, detach



class BaseOrgtagHandler(BaseTagHandler):
    Tag = Orgtag
    Entity = Org
    tag_id = "orgtag_id"
    entity_id = "org_id"
    cross_table = org_orgtag

    def _get_orgtag(self, orgtag_id_string, options=None):
        orgtag_id = int(orgtag_id_string)

        query = self.orm.query(Orgtag)\
            .filter_by(orgtag_id=orgtag_id)

        if not self.moderator:
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

    def _create_orgtag(self):
        name, public = BaseOrgtagHandler._get_arguments(self)

        moderation_user = self.current_user

        orgtag = Orgtag(
            name,
            moderation_user=moderation_user, public=public,)

        detach(orgtag)

        return orgtag

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
        return self._create_orgtag

    @property
    def _get(self):
        return self._get_orgtag

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
                type_title="Organisation",
                type_title_plural="Organisations",
                type_url="organisation",
                type_entity_list="org_list",
                type_li_template="org_li",
                type_length="org_len",
                )



class OrgtagNewHandler(BaseOrgtagHandler):
    @authenticated
    def get(self):
        path_list = self._get_path_list()
        self.render(
            'tag.html',
            type_title="Organisation",
            type_title_plural="Organisations",
            type_url="organisation",
            type_entity_list="org_list",
            type_li_template="org_li",
            path_list=path_list,
            )



class OrgtagHandler(BaseOrgtagHandler,
                    MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_orgtag

    @property
    def _get(self):
        return self._get_orgtag

    def _before_delete(self, orgtag):
        if orgtag.org_list:
            raise HTTPError(405, "Cannot delete tag because it has attached organisations.")

    def get(self, orgtag_id_string):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_offset = self.get_argument_int("note_offset", None)

        public = self.moderator

        orgtag = self._get_orgtag(orgtag_id_string)

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
            org_obj_list=org_list,
            note_obj_list=note_list,
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
                type_title="Organisation",
                type_title_plural="Organisations",
                type_url="organisation",
                type_entity_list="org_list",
                type_li_template="org_li",
                path_list=path_list,
                )



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
        self.orm_commit()
        return self.redirect_next(orgtag.url)

    @authenticated
    def get(self, orgtag_id_string): 
        orgtag = self._get_orgtag(orgtag_id_string)

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
    def put(self, orgtag_id_string, note_id_string):
        orgtag = self._get_orgtag(orgtag_id_string)
        note = self._get_note(note_id_string)
        if note not in orgtag.note_list:
            orgtag.note_list.append(note)
            self.orm_commit()
        return self.redirect_next(orgtag.url)

    @authenticated
    def delete(self, orgtag_id_string, note_id_string):
        orgtag = self._get_orgtag(orgtag_id_string)
        note = self._get_note(note_id_string)
        if note in orgtag.note_list:
            orgtag.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(orgtag.url)



