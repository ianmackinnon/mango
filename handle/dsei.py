# -*- coding: utf-8 -*-

import json
from base import BaseHandler
from model import Orgtag



class DseiTagListHandler(BaseHandler):
    def get(self):
        cache_key = "dsei-tag"
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
                u"Military export applicant to % in 2010")
                    ) \
            .all()

        tag_list = []
        for tag in results:
            tag_list.append({
                    "label": tag.name[38:-8],
                    "value": tag.base_short,
                    })

        tag_list.sort()
        self.cache.set(cache_key, json.dumps(tag_list))
        self.write_json(tag_list)



class DseiOrgListHandler(BaseHandler):
    def get(self):
        cache_key = "dsei-org"
        value = self.cache.get(cache_key)
        if value:
            self.set_header(
                "Content-Type",
                "application/json; charset=UTF-8"
                )
            self.write(value)
            self.finish()
            return

        dsei_tag = self.orm.query(Orgtag) \
            .filter(Orgtag.base_short==u"dsei-2013") \
            .first()

        org_list = []

        if dsei_tag:
            for org in dsei_tag.org_list_public:
                org_list.append({
                        "label": org.name,
                        "value": org.url,
                        })

        org_list.sort()
        self.cache.set(cache_key, json.dumps(org_list))
        self.write_json(org_list)



class DseiHandler(BaseHandler):
    def get(self):
        self.render(
            'dsei.html',
            )



        


