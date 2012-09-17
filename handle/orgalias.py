# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from tornado.web import HTTPError

from base import BaseHandler, authenticated

from model import Org, Orgalias



class BaseOrgaliasHandler(BaseHandler): 
    def _get_orgalias(self, orgalias_id_string, options=None):
        orgalias_id = int(orgalias_id_string)

        query = self.orm.query(Orgalias)\
            .filter_by(orgalias_id=orgalias_id)

        if not self.current_user:
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

    def _get_arguments(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)
        public = self.get_argument_public("public", json=is_json)

        return name, public



class OrgaliasHandler(BaseOrgaliasHandler):
    @authenticated
    def get(self, orgalias_id_string):
        public = bool(self.current_user)

        options = (
                joinedload("org"),
                )

        orgalias = self._get_orgalias(orgalias_id_string, options)

        obj = orgalias.obj(
            public=public,
            org_obj = orgalias.org.obj(public=public),
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'alias.html',
                obj=obj,
                type_title="Organisation",
                type_title_plural="Organisations",
                type_url="organisation",
                type_entity_list="org_list",
                type_li_template="org_li",
                )

    @authenticated
    def delete(self, orgalias_id_string):
        orgalias = self._get_orgalias(orgalias_id_string)
        self.orm.delete(orgalias)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + "/organisation")

    @authenticated
    def put(self, orgalias_id_string):
        orgalias = self._get_orgalias(orgalias_id_string)
        name, public = BaseOrgaliasHandler._get_arguments(self)

        if orgalias.name == name and \
                orgalias.public == public:
            self.redirect(self.next or self.url_root[:-1] + orgalias.url)
            return
            
        orgalias.name = name
        orgalias.public = public
        orgalias.moderation_user = self.current_user
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + orgalias.url)
