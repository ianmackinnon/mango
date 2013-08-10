# -*- coding: utf-8 -*-

from base import BaseHandler
from model import Orgtag



class DseiTagListHandler(BaseHandler):
    def get(self):
        results = self.orm.query(Orgtag) \
            .filter(Orgtag.base.contains("Military export applicant to % in 2010")) \
            .all()

        tag_list = []
        for tag in results:
            tag_list.append({
                    "label": tag.name[38:-8],
                    "value": tag.base_short,
                    })

        tag_list.sort()
        self.write_json(tag_list)



class DseiHandler(BaseHandler):
    def get(self):
        self.render(
            'dsei.html',
            )



        


