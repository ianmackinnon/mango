
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



class FairMixin(object):
    # Optionally override
    name = None
    year = None

    @property
    def tag_name(self):
        if not (self.name and self.year):
            return None
        return "%s-%d" % (self.name, self.year)




class HomeTargetListHandler(FairMixin, BaseHandler):
    def get(self):
        visibility = self.parameters.get("visibility", None)

        cache_key = "country-tag-%s-%s" % (self.tag_name or "home", visibility)

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
        if self.tag_name:
            q1 = q1 \
                .join(org_orgtag) \
                .join(Orgtag) \
                .filter(Orgtag.base_short == self.tag_name)
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
            "year": self.year,
            "tagName": self.tag_name,
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



class FairHandler(FairMixin, BaseHandler):
    def get(self):
        self.load_map = True
        self.render(
            '%s.html' % self.name,
            name=self.name,
            year=self.year,
            tag_name=self.tag_name,
        )



class FairOrgListHandler(FairMixin, BaseHandler):
    @property
    def org_cache_key(self):
        return self.tag_name and ("%s-org" % self.tag_name)

    def get(self):
        value = self.cache.get(self.org_cache_key)
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
        self.cache.set(self.org_cache_key, json.dumps(org_list))
        self.write_json(org_list)



class DseiMixin(object):
    name = "dsei"
    year = 2015
class DseiHandler(DseiMixin, FairHandler):
    pass
class DseiTargetListHandler(DseiMixin, HomeTargetListHandler):
    pass
class DseiOrgListHandler(DseiMixin, FairOrgListHandler):
    pass



class DprteMixin(object):
    name = "dprte"
    year = 2017
class DprteHandler(DprteMixin, FairHandler):
    pass
class DprteTargetListHandler(DprteMixin, HomeTargetListHandler):
    pass
class DprteOrgListHandler(DprteMixin, FairOrgListHandler):
    pass



class FarnboroughMixin(object):
    name = "farnborough"
    year = 2016
class FarnboroughHandler(FarnboroughMixin, FairHandler):
    pass
class FarnboroughTargetListHandler(FarnboroughMixin, HomeTargetListHandler):
    pass
class FarnboroughOrgListHandler(FarnboroughMixin, FairOrgListHandler):
    pass



class SecPolMixin(object):
    name = "security-and-policing"
    year = 2016
class SecPolHandler(SecPolMixin, FairHandler):
    pass
class SecPolTargetListHandler(SecPolMixin, HomeTargetListHandler):
    pass
class SecPolOrgListHandler(SecPolMixin, FairOrgListHandler):
    pass
