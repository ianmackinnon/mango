
from sqlalchemy.sql import func
from tornado.web import HTTPError

from model import Org, Orgtag, org_orgtag

from handle.base import authenticated, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from handle.base_tag import BaseTagHandler
from handle.note import BaseNoteHandler



class BaseOrgtagHandler(BaseTagHandler):
    Tag = Orgtag
    Entity = Org
    tag_id = "orgtag_id"
    entity_id = "org_id"
    tag_type = "orgtag"
    entity_type = "org"
    cross_table = org_orgtag

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
            raise HTTPError(404)

        return MangoEntityListHandlerMixin.post(self)

    def get(self):
        (orgtag_list, _name, _name_short, _base, _base_short,
         path, search, sort) = self._get_tag_search_args()

        if self.accept_type("json"):
            self.write_json(orgtag_list)
        else:
            self.render(
                'tag-list.html',
                tag_list=orgtag_list,
                path=path,
                search=search,
                sort=sort,
                visibility=self.parameters.get("visibility", None),
                type_title="Company",
                type_title_plural="Companies",
                type_url="organisation",
                type_entity_list="orgList",
                type_li_template="org_li",
                type_length="org_len",
                )



class OrgtagNewHandler(BaseOrgtagHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        if self.parameters.get("view", None) != "edit":
            self.next_ = "/orgtag"
            self.redirect_next()
            return

        path_list = self._get_path_list()
        self.render(
            'tag.html',
            type_title="Company",
            type_title_plural="Companies",
            type_url="organisation",
            type_entity_list="orgList",
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
            raise HTTPError(
                405, "Cannot delete tag because it has attached organisations.")

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

    def get(self, orgtag_id):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)
        note_offset = self.get_argument_int("note_offset", None)

        public = self.moderator

        orgtag = self._get_tag(orgtag_id)

        org_list_query = self.orm.query(Org) \
            .join(org_orgtag) \
            .filter(
                Org.org_id == org_orgtag.c.org_id,
                org_orgtag.c.orgtag_id == orgtag.orgtag_id,
            )
        org_list_query = self.filter_visibility(
            org_list_query,
            Org,
            visibility=self.parameters.get("visibility", None),
            )
        org_list = org_list_query \
            .order_by(Org.name) \
            .all()

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
                type_entity_list="orgList",
                type_li_template="org_li",
                path_list=path_list,
                )



class OrgtagNoteListHandler(BaseOrgtagHandler, BaseNoteHandler):
    @authenticated
    def post(self, orgtag_id):
        if not self.moderator:
            raise HTTPError(404)

        orgtag = self._get_tag(orgtag_id)
        note = self._create_note()
        orgtag.note_list.append(note)
        self.orm_commit()
        return self.redirect_next(orgtag.url)

    @authenticated
    def get(self, orgtag_id):
        if not self.moderator:
            raise HTTPError(404)

        orgtag = self._get_tag(orgtag_id)

        obj = orgtag.obj(
            public=self.moderator,
            )
        self.next_ = orgtag.url
        self.render(
            'note.html',
            entity=obj
            )



class OrgtagNoteHandler(BaseOrgtagHandler, BaseNoteHandler):
    @authenticated
    def put(self, orgtag_id, note_id):
        if not self.moderator:
            raise HTTPError(404)

        orgtag = self._get_tag(orgtag_id)
        note = self._get_note(note_id)
        if note not in orgtag.note_list:
            orgtag.note_list.append(note)
            self.orm_commit()
        return self.redirect_next(orgtag.url)

    @authenticated
    def delete(self, orgtag_id, note_id):
        if not self.moderator:
            raise HTTPError(404)

        orgtag = self._get_tag(orgtag_id)
        note = self._get_note(note_id)
        if note in orgtag.note_list:
            orgtag.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(orgtag.url)



class OrgtagActivityHandler(BaseOrgtagHandler):
    def get(self):
        # pylint: disable=singleton-comparison
        # Cannot use `is` in SQLAlchemy filters

        path_list = ['activity', 'activity-exclusion']

        visibility = self.parameters.get("visibility", None)

        q1 = self.orm.query(org_orgtag.c.orgtag_id) \
            .join(Org, org_orgtag.c.org_id == Org.org_id) \
            .add_columns(Org.org_id)
        q1 = self.filter_visibility(q1, Org, visibility=visibility)
        s1 = q1.subquery()

        q2 = self.orm.query(Orgtag) \
             .outerjoin(s1, Orgtag.orgtag_id == s1.c.orgtag_id) \
             .add_columns(func.count(s1.c.org_id).label("count"))
        q2 = self.filter_visibility(q2, Orgtag, visibility='all')
        q2 = q2 \
            .filter(
                Orgtag.path_short.in_(path_list),
                Orgtag.is_virtual == None,
            ) \
            .group_by(Orgtag.orgtag_id) \
            .order_by(Orgtag.path_short, Orgtag.name_short)

        orgtag_list = []
        for orgtag, count in q2.all():
            obj = orgtag.obj(public=True)
            obj.update({
                "count": count,
            })
            orgtag_list.append(obj)

        self.render(
            'moderation-orgtag-activity.html',
            orgtag_list=orgtag_list,
            )



class ModerationOrgtagActivityHandler(OrgtagActivityHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)
        return OrgtagActivityHandler.get(self)
