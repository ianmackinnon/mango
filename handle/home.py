
import json

from sqlalchemy.sql import func

from model import Org, Orgtag, org_orgtag

from handle.base import BaseHandler



class NotFoundHandler(BaseHandler):
    _unsupported_method_error = (404, "Not Found")
    _unsupported_methods = [True]



class HomeRedirectHandler(BaseHandler):
    def get(self):
        self.redirect(self.url_root + "security-and-policing")
        return



class HomeHandler(BaseHandler):
    def get(self):
        self.load_map = True
        self.render('home.html')



class HomeTargetListHandler(BaseHandler):
    tag_base = None

    def get(self):
        visibility = self.parameters.get("visibility", None)

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
                .filter(Orgtag.base_short == self.tag_base)
        q1 = q1 \
            .subquery()

        q2 = self.orm.query(func.substr(Orgtag.base, 30), Orgtag.base_short) \
            .join(org_orgtag, Orgtag.orgtag_id == org_orgtag.c.orgtag_id) \
            .join(q1, q1.c.org_id == org_orgtag.c.org_id) \
            .add_columns(func.count(q1.c.org_id)) \
            .filter(
                Orgtag.path_short == "market",
                Orgtag.base_short.startswith("military-export-applicant-to-%"),
                ~Orgtag.base_short.startswith(
                    "military-export-applicant-to-%-in-____"),
            ) \
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
            obj = {
                "label": org.name,
                "value": org.url,
            }
            if org.orgalias_list_public:
                obj["alias"] = []
                for orgalias in org.orgalias_list_public:
                    obj["alias"].append(orgalias.name)
            org_list.append(obj)

        org_list.sort(key=lambda x: x["label"])
        self.cache.set(cache_key, json.dumps(org_list))
        self.write_json(org_list)



class FairHandler(BaseHandler):
    # Override:
    name = None
    tag_name = None

    def get(self):
        self.load_map = True
        self.render(
            '%s.html' % self.name,
            tag_name=self.tag_name,
            )

class FairOrgListHandler(BaseHandler):
    # Override:
    cache_key = None
    tag_name = None

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
            .filter(Orgtag.base_short == self.tag_name) \
            .first()

        org_list = []

        if tag:
            for org in tag.org_list_public:
                obj = {
                    "label": org.name,
                    "value": org.url,
                    }
                if org.orgalias_list_public:
                    obj["alias"] = []
                    for orgalias in org.orgalias_list_public:
                        obj["alias"].append(orgalias.name)
                org_list.append(obj)

        org_list.sort(key=lambda x: x["label"])
        self.cache.set(self.cache_key, json.dumps(org_list))
        self.write_json(org_list)



class DseiHandler(FairHandler):
    name = "dsei"
    tag_name = "dsei-2015"

class DseiTargetListHandler(HomeTargetListHandler):
    tag_base = "dsei-2015"

class DseiOrgListHandler(FairOrgListHandler):
    cache_key = "dsei-org"
    tag_name = "dsei-2015"



class DprteHandler(FairHandler):
    name = "dprte"
    tag_name = "dprte-2016"

class DprteTargetListHandler(HomeTargetListHandler):
    tag_base = "dprte-2016"

class DprteOrgListHandler(FairOrgListHandler):
    cache_key = "dprte-org"
    tag_name = "dprte-2016"



class FarnboroughHandler(FairHandler):
    name = "farnborough"
    tag_name = "farnborough-2016"

class FarnboroughTargetListHandler(HomeTargetListHandler):
    tag_base = "farnborough-2016"

class FarnboroughOrgListHandler(FairOrgListHandler):
    cache_key = "farnborough-org"
    tag_name = "farnborough-2016"



class SecurityPolicingHandler(FairHandler):
    name = "security-and-policing"
    tag_name = "security-and-policing-2016"

class SecurityPolicingTargetListHandler(HomeTargetListHandler):
    tag_base = "security-and-policing-2016"

class SecurityPolicingOrgListHandler(FairOrgListHandler):
    cache_key = "security-and-policing-org"
    tag_name = "security-and-policing-2016"
