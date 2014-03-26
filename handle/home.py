# -*- coding: utf-8 -*-

import json

from base import BaseHandler
from model import Org, Orgtag



class HomeHandler(BaseHandler):
    def get(self):
        self.render('home.html')



class CountryTagListHandler(BaseHandler):
    def get(self):
        """
        Returns all possible country tag names.
        Does not take into account visibility or existance of orgs
        in those categories.
        """

        cache_key = "country-tag"
        value = self.cache.get(cache_key)
        if value:
            self.set_header(
                "Content-Type",
                "application/json; charset=UTF-8"
                )
            self.write(value)
            self.finish()
            return

        results = self.orm.query(Orgtag) \
            .filter(Orgtag.base.contains(
                u"Military export applicant to % in %")
                    ) \
            .all()

        tag_dict = {}
        for tag in results:
            name = tag.name[38:-8]
            if not name in tag_dict:
                tag_dict[name] = []
            tag_dict[name].append(tag.base_short)

        tag_list = []
        for key in sorted(tag_dict.keys()):
            tag_list.append({
                    "label": key,
                    "value": ",".join(tag_dict[key])
                    })

        self.cache.set(cache_key, json.dumps(tag_list))
        self.write_json(tag_list)



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
        self.render(
            '%s.html' % self.name,
            tag_name=self.tag_name,
            )

class DseiHandler(FairHandler):
    name = "dsei"
    tag_name = "dsei-2013"

class FarnboroughHandler(FairHandler):
    name = "farnborough"
    tag_name = "farnborough-2014"



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

