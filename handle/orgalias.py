# -*- coding: utf-8 -*-

from sqlalchemy.orm.exc import NoResultFound
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



class OrgaliasHandler(BaseOrgaliasHandler):
    @authenticated
    def delete(self, orgalias_id_string):
        orgalias = self._get_orgalias(orgalias_id_string)
        self.orm.delete(orgalias)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + "/organisation")
