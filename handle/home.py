# -*- coding: utf-8 -*-

import json

from sqlalchemy.sql import func
from tornado.web import HTTPError

from base import BaseHandler
from model import Org, Orgtag, org_orgtag



class NotFoundHandler(BaseHandler):
    _unsupported_method_error = (404, "Not Found")
    _unsupported_methods = [True]



class HomeRedirectHandler(BaseHandler):
    def get(self):
        self.redirect(self.url_root + "farnborough")
        return



class HomeHandler(BaseHandler):
    def get(self):
        self.load_map = True
        self.render('home.html')



class HomeTargetListHandler(BaseHandler):
    tag_base = None

    def get(self):
        visibility=self.parameters.get("visibility", None)

        cache_key = "country-tag-%s-%s" % (self.tag_base or "home", visibility)

        value = self.cache.get(cache_key)
        if value:
            self.set_header(
                "Content-Type",
                "application/json; charset=UTF-8"
                )
            self.write(value)
            self.finish()
            return

        q1 = self.orm.query(Org.org_id.label("org_id"))
        q1 = self.filter_visibility(
            q1, Org, visibility)
        if self.tag_base:
            q1 = q1 \
                .join(org_orgtag) \
                .join(Orgtag) \
                .filter(Orgtag.base_short==self.tag_base)
        q1 = q1 \
            .subquery()

        q2 = self.orm.query(func.substr(Orgtag.base, 30), Orgtag.base_short) \
            .join(org_orgtag, Orgtag.orgtag_id==org_orgtag.c.orgtag_id) \
            .join(q1, q1.c.org_id==org_orgtag.c.org_id) \
            .add_columns(func.count(q1.c.org_id)) \
            .filter(Orgtag.path_short==u"market") \
            .filter(Orgtag.base_short.startswith(u"military-export-applicant-to-%")) \
            .filter(~Orgtag.base_short.startswith(u"military-export-applicant-to-%-in-____")) \
            .group_by(Orgtag.orgtag_id) \
            .order_by(Orgtag.base)

        results = q2.all()

        data = {
            "tagName": self.tag_base,
            "countries": results
        }

        self.cache.set(cache_key, json.dumps(data))
        self.write_json(data)



class HomeOrgListHandler(BaseHandler):
    def get(self):
        cache_key = "home-org"
        value = self.cache.get(cache_key)
        if value:
            self.set_header(
                "Content-Type",
                "application/json; charset=UTF-8"
                )
            self.write(value)
            self.finish()
            return

        org_list = []

        for org in self.orm.query(Org).filter_by(public=True).all():
            org_list.append({
                    "label": org.name,
                    "value": org.url,
                    })

        org_list.sort()
        self.cache.set(cache_key, json.dumps(org_list))
        self.write_json(org_list)



class FairHandler(BaseHandler):
    def get(self):
        self.load_map = True
        self.render(
            '%s.html' % self.name,
            tag_name=self.tag_name,
            )

class DseiHandler(FairHandler):
    name = "dsei"
    tag_name = u"dsei-2015"

class FarnboroughHandler(FairHandler):
    name = "farnborough"
    tag_name = u"farnborough-2014"

class DseiTargetListHandler(HomeTargetListHandler):
    tag_base = u"dsei-2015"

class FarnboroughTargetListHandler(HomeTargetListHandler):
    tag_base = u"farnborough-2014"



class FairOrgListHandler(BaseHandler):
    def get(self):
        value = self.cache.get(self.cache_key)
        if value:
            self.set_header(
                "Content-Type",
                "application/json; charset=UTF-8"
                )
            self.write(value)
            self.finish()
            return

        tag = self.orm.query(Orgtag) \
            .filter(Orgtag.base_short==self.tag_name) \
            .first()

        org_list = []

        if tag:
            for org in tag.org_list_public:
                org_list.append({
                        "label": org.name,
                        "value": org.url,
                        })

        org_list.sort()
        self.cache.set(self.cache_key, json.dumps(org_list))
        self.write_json(org_list)

class DseiOrgListHandler(FairOrgListHandler):
    cache_key = "dsei-org"
    tag_name = u"dsei-2013"

class FarnboroughOrgListHandler(FairOrgListHandler):
    cache_key = "farnborough-org"
    tag_name = u"farnborough-2014"

