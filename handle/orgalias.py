
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from tornado.web import HTTPError

from model import Orgalias

from handle.base import BaseHandler, authenticated




class BaseOrgaliasHandler(BaseHandler):
    def _get_orgalias(self, orgalias_id, options=None):
        query = self.orm.query(Orgalias)\
            .filter_by(orgalias_id=orgalias_id)

        if not self.moderator:
            query = query \
                .filter_by(public=True)

        if options:
            query = query \
                .options(*options)

        try:
            orgalias = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d: No such orgalias" % orgalias_id)

        return orgalias

    def _get_entity_arguments(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", is_json=is_json)
        public = self.get_argument_public("public", is_json=is_json)

        return name, public



class OrgaliasHandler(BaseOrgaliasHandler):
    @authenticated
    def get(self, orgalias_id):
        if not self.moderator:
            raise HTTPError(404)

        public = True

        options = (
            joinedload("org"),
        )

        orgalias = self._get_orgalias(orgalias_id, options)

        if self.parameters.get("view", None) != "edit":
            self.next_ = orgalias.org.url
            self.redirect_next()
            return

        obj = orgalias.obj(
            public=public,
            org=orgalias.org.obj(public=public),
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'alias.html',
                obj=obj,
                type_title="Company",
                type_title_plural="Companies",
                type_url="organisation",
                type_entity_list="org_list",
                type_li_template="org_li",
                )

    @authenticated
    def delete(self, orgalias_id):
        if not self.moderator:
            raise HTTPError(404)

        orgalias = self._get_orgalias(orgalias_id)
        self.orm.delete(orgalias)
        self.orm_commit()
        return self.redirect_next("/organisation")

    @authenticated
    def put(self, orgalias_id):
        if not self.moderator:
            raise HTTPError(404)

        orgalias = self._get_orgalias(orgalias_id)
        name, public = BaseOrgaliasHandler._get_entity_arguments(self)

        print(name, public)

        if orgalias.name == name and \
                orgalias.public == public:
            return self.redirect_next(orgalias.url)

        orgalias.name = name
        orgalias.public = public
        orgalias.moderation_user = self.current_user
        self.orm_commit()
        return self.redirect_next(orgalias.url)
