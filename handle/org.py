# -*- coding: utf-8 -*-

import json

from collections import OrderedDict

from sqlalchemy import distinct, or_, and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy.sql import exists, func, literal
from sqlalchemy.sql.expression import case
from tornado.web import HTTPError

from base import BaseHandler, authenticated, sha1_concat
from note import BaseNoteHandler
from orgtag import BaseOrgtagHandler
from address import BaseAddressHandler

from model import Org, Note, Address, Orgalias, Orgtag, org_orgtag, org_address



max_address_per_page = 26
max_address_pages = 3



class BaseOrgHandler(BaseHandler):
    def _get_org(self, org_id_string, options=None):
        org_id = int(org_id_string)

        query = self.orm.query(Org)\
            .filter_by(org_id=org_id)

        if options:
            query = query \
                .options(*options)

        if not self.current_user:
            query = query \
                .filter_by(public=True)

        try:
            org = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d: No such org" % org_id)

        return org
    
    def _get_name_search_query(self, name=None, name_search=None,
                               visibility=None):

        org_name_query = self.orm.query(
            Org.name.label("name"),
            Org.org_id.label("org_id"),
            literal(None).label('orgalias_id')
            )
        org_name_query = self.filter_visibility(
            org_name_query, Org, visibility)
        orgalias_name_query = self.orm.query(
            Orgalias.name.label("name"),
            Org.org_id.label("org_id"),
            Orgalias.orgalias_id.label('orgalias_id')
            ) \
            .join(Orgalias.org)
        # Non-private orgaliases are not for the site, only robots
        orgalias_name_query = self.filter_visibility(
            orgalias_name_query, Orgalias, True)
        # Orgs get filtered on visibility just the same
        orgalias_name_query = self.filter_visibility(
            orgalias_name_query, Org, visibility)
        name_subquery = org_name_query.union_all(orgalias_name_query).subquery()

        name_query = self.orm.query(
            name_subquery.c.org_id,
            case(
                [(
                        func.count("*") > func.count(name_subquery.c.orgalias_id),
                        literal(None),
                        ),],
                else_=func.min(name_subquery.c.orgalias_id),
                ).label("orgalias_id")
            )

        if name:
            name_query = name_query \
                .filter(name_subquery.c.name==name)
        elif name_search:
            name_query = name_query \
                .filter(name_subquery.c.name.contains(name_search)) \
                .order_by(
                name_subquery.c.name.startswith(name_search).desc(),
                name_subquery.c.name
                )
        else:
            name_query = name_query \
                .order_by(name_subquery.c.name)

        name_query = name_query \
            .group_by(name_subquery.c.org_id)

        return name_query



    def _get_org_alias_search_query(
        self, name=None, name_search=None,
        tag_name_list=None, visibility=None):

        name_query = self._get_name_search_query(name, name_search, visibility)
        name_subquery = name_query.subquery()

        org_alias_query = self.orm.query(Org, Orgalias) \
            .join(name_subquery, Org.org_id==name_subquery.c.org_id) \
            .outerjoin(Orgalias, Orgalias.orgalias_id==name_subquery.c.orgalias_id)
        
        if tag_name_list:
            org_alias_query = org_alias_query \
                .join((Orgtag, Org.orgtag_list)) \
                .filter(Orgtag.short.in_(tag_name_list))
            org_alias_query = self.filter_visibility(
                org_alias_query, Orgtag, visibility, secondary=True)

        return org_alias_query



    def _get_org_packet_search(self, name=None, name_search=None,
                               tag_name_list=None,
                               location=None,
                               visibility=None,
                               offset=None,
                               view="org"):

        org_alias_query = self._get_org_alias_search_query(
            name=name,
            name_search=name_search,
            tag_name_list=tag_name_list,
            visibility=visibility,
            )

        if location:
            org_alias_address_query = org_alias_query \
                .join(Org.address_list)
        else:
            org_alias_address_query = org_alias_query \
                .outerjoin(Org.address_list)
            

        org_alias_address_query = org_alias_address_query \
            .add_entity(Address)
        org_alias_address_query = self.filter_visibility(
            org_alias_address_query, Address, visibility,
            secondary=True, null_column=Address.address_id)

        if location:
            org_alias_address_query = org_alias_address_query \
                .filter(and_(
                    Address.latitude != None,
                    Address.latitude >= location.south,
                    Address.latitude <= location.north,
                    Address.longitude != None,
                    Address.longitude >= location.west,
                    Address.longitude <= location.east,
                    ))

        if offset:
            org_alias_address_query = org_alias_address_query \
                .offset(offset)

        org_packet = {
            "location": location and location.to_obj(),
            }

        if (view == "marker" or
            org_alias_address_query.count() > max_address_per_page * max_address_pages
            ):
            org_packet["marker_list"] = []
            for org, alias, address in org_alias_address_query:
                org_packet["marker_list"].append({
                        "name": org.name,
                        "url": org.url,
                        "latitude": address and address.latitude,
                        "longitude": address and address.longitude,
                        })
        else:
            orgs = OrderedDict()
            for org, alias, address in org_alias_address_query:
                if not org.org_id in orgs:
                    orgs[org.org_id] = {
                        "org": org,
                        "alias": alias and alias.name,
                        "address_obj_list": [],
                        }
                if address:
                    orgs[org.org_id]["address_obj_list"].append(address.obj(
                            public=bool(self.current_user)
                            ))

            org_packet["org_list"] = []
            for org_id, data in orgs.items():
                org_packet["org_list"].append(data["org"].obj(
                        public=bool(self.current_user),
                        address_obj_list=data["address_obj_list"],
                        alias=data["alias"],
                        ))

        return org_packet



class OrgListHandler(BaseOrgHandler, BaseOrgtagHandler):
    @staticmethod
    def _cache_key(name_search, tag_name_list, view, visibility):
        if not visibility:
            visibility = "public"
        return sha1_concat(json.dumps({
                "nameSearch": name_search,
                "tag": tuple(set(tag_name_list)),
                "visibility": visibility,
                "view": view,
                }))
    
    def get(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("nameSearch", None, json=is_json)
        tag_name_list = self.get_arguments_multi("tag", json=is_json)
        location = self.get_argument_geobox("location", None, json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)
        view = self.get_argument_allowed("view", ["org", "marker"],
                                         default="org", json=is_json)

        if self.has_javascript and not self.accept_type("json"):
            self.render(
                'organisation_list.html',
                name=name,
                name_search=name_search,
                tag_name_list=tag_name_list,
                location=location and location.to_obj(),
                offset=offset,
                )
            return;

        cache_key = None
        if 0 and self.accept_type("json") and not location and not offset:
            cache_key = self._cache_key(name_search, tag_name_list, view,
                                        self.parameters["visibility"])
            value = self.cache.get(cache_key)
            if value:
                self.set_header("Content-Type", "application/json; charset=UTF-8")
                self.write(value)
                self.finish()
                return

        org_packet = self._get_org_packet_search(
            name=name,
            name_search=name_search,
            tag_name_list=tag_name_list,
            location=location,
            visibility=self.parameters["visibility"],
            offset=offset,
            view=view,
            )

        if cache_key:
            self.cache.set(cache_key, json.dumps(org_packet))

        if self.accept_type("json"):
            self.write_json(org_packet)
        else:
            self.render(
                'organisation_list.html',
                org_packet=org_packet,
                name=name,
                name_search=name_search,
                tag_name_list=tag_name_list,
                location=location and location.to_obj(),
                offset=offset,
                )

    @authenticated
    def post(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)
        public = self.get_argument_public("public", json=is_json)

        org = Org(name, moderation_user=self.current_user, public=public)
        self.orm.add(org)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)



class OrgNewHandler(BaseOrgHandler):
    @authenticated
    def get(self):
        self.render(
            'organisation.html',
            )



class OrgHandler(BaseOrgHandler):
    def get_note_arguments(self):
        is_json = self.content_type("application/json")
        note_search = self.get_argument("note_search", None, json=is_json)
        note_order = self.get_argument_order("note_order", None, json=is_json)
        note_offset = self.get_argument_int("note_offset", None, json=is_json)
        return note_search, note_order, note_offset

    def get(self, org_id_string):
        note_search, note_order, note_offset = self.get_note_arguments()

        public = bool(self.current_user)

        org = self._get_org(org_id_string)

        if self.deep_visible():
            address_list=org.address_list
            orgtag_list=org.orgtag_list
            event_list=org.event_list
            orgalias_list=org.orgalias_list
        else:
            address_list=org.address_list_public
            orgtag_list=org.orgtag_list_public
            event_list=org.event_list_public
            orgalias_list=org.orgalias_list_public

        note_list, note_count = org.note_list_filtered(
            note_search=note_search,
            note_order=note_order,
            note_offset=note_offset,
            all_visible=self.deep_visible(),
            )

        address_list = [address.obj(public=public) for address in address_list]
        orgtag_list = [orgtag.obj(public=public) for orgtag in orgtag_list]
        note_list = [note.obj(public=public) for note in note_list]
        event_list = [event.obj(public=public) for event in event_list]
        orgalias_list = [orgalias.obj(public=public) for orgalias in orgalias_list]

        obj = org.obj(
            public=public,
            address_obj_list=address_list,
            orgtag_obj_list=orgtag_list,
            note_obj_list=note_list,
            note_count=note_count,
            event_obj_list=event_list,
            orgalias_obj_list=orgalias_list,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'organisation.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                )

    @authenticated
    def delete(self, org_id_string):
        org = self._get_org(org_id_string)
        self.orm.delete(org)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + "/organisation")
        
    @authenticated
    def put(self, org_id_string):
        org = self._get_org(org_id_string)

        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)
        public = self.get_argument_public("public", json=is_json)

        if org.name == name and \
                org.public == public:
            self.redirect(self.next or self.url_root[:-1] + org.url)
            return

        org.name = name
        org.public = public
        org.moderation_user = self.current_user
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)
        


class OrgAddressListHandler(BaseOrgHandler, BaseAddressHandler):
    @authenticated
    def get(self, org_id_string):
        public = bool(self.current_user)
        org = self._get_org(org_id_string)

        obj = org.obj(
            public=public,
            )

        self.render(
            'address.html',
            address=None,
            entity=obj,
            entity_list="org_list",
            )
        
    @authenticated
    def post(self, org_id_string):
        org = self._get_org(org_id_string)

        postal, source, lookup, manual_longitude, manual_latitude, \
            public = \
            BaseAddressHandler._get_arguments(self)

        address = Address(postal, source, lookup,
                              manual_longitude=manual_longitude,
                              manual_latitude=manual_latitude,
                              moderation_user=self.current_user,
                              public=public,
                              )
        address.geocode()
        org.address_list.append(address)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)



class OrgNoteListHandler(BaseOrgHandler, BaseNoteHandler):
    @authenticated
    def post(self, org_id_string):
        org = self._get_org(org_id_string)

        text, source, public = BaseNoteHandler._get_arguments(self)
        
        note = Note(text, source,
                    moderation_user=self.current_user,
                    public=public,
                    )
        org.note_list.append(note)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)

    @authenticated
    def get(self, org_id_string):
        org = self._get_org(org_id_string)
        public = bool(self.current_user)
        obj = org.obj(
            public=public,
            )
        self.next = org.url
        self.render(
            'note.html',
            entity=obj
            )



class OrgAddressHandler(BaseOrgHandler, BaseAddressHandler):
    @authenticated
    def put(self, org_id_string, address_id_string):
        org = self._get_org(org_id_string)
        address = self._get_address(address_id_string)
        if address not in org.address_list:
            org.address_list.append(address)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)

    @authenticated
    def delete(self, org_id_string, address_id_string):
        org = self._get_org(org_id_string)
        address = self._get_address(address_id_string)
        if address in org.address_list:
            org.address_list.remove(address)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)



class OrgNoteHandler(BaseOrgHandler, BaseNoteHandler):
    @authenticated
    def put(self, org_id_string, note_id_string):
        org = self._get_org(org_id_string)
        note = self._get_note(note_id_string)
        if note not in org.note_list:
            org.note_list.append(note)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)

    @authenticated
    def delete(self, org_id_string, note_id_string):
        org = self._get_org(org_id_string)
        note = self._get_note(note_id_string)
        if note in org.note_list:
            org.note_list.remove(note)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)



class OrgOrgtagListHandler(BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def get(self, org_id_string):

        # org...

        org = self._get_org(org_id_string)

        if self.deep_visible():
            orgtag_list=org.orgtag_list
        else:
            orgtag_list=org.orgtag_list_public

        public = bool(self.current_user)

        orgtag_list = [orgtag.obj(public=public) for orgtag in orgtag_list]

        obj = org.obj(
            public=public,
            orgtag_obj_list=orgtag_list,
            )

        # orgtag...

        orgtag_and_org_count_list, name, short, search = \
            BaseOrgtagHandler._get_orgtag_and_org_count_list_search_and_args(self)

        orgtag_list = []
        for orgtag, org_count in orgtag_and_org_count_list:
            orgtag_list.append(orgtag.obj(
                    public=bool(self.current_user),
                    org_len=org_count,
                    ))

        self.render(
            'entity_tag.html',
            obj=obj,
            tag_list=orgtag_list,
            search=search,
            type_title="Organisation",
            type_title_plural="Organisations",
            type_url="organisation",
            type_tag_list="orgtag_list",
            type_entity_list="org_list",
            type_li_template="org_li",
            )



class OrgOrgtagHandler(BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def put(self, org_id_string, orgtag_id_string):
        org = self._get_org(org_id_string)
        orgtag = self._get_orgtag(orgtag_id_string)
        if orgtag not in org.orgtag_list:
            org.orgtag_list.append(orgtag)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)

    @authenticated
    def delete(self, org_id_string, orgtag_id_string):
        org = self._get_org(org_id_string)
        orgtag = self._get_orgtag(orgtag_id_string)
        if orgtag in org.orgtag_list:
            org.orgtag_list.remove(orgtag)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)



class OrgOrgaliasListHandler(BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def get(self, org_id_string):
        # org...

        org = self._get_org(org_id_string)

        if self.deep_visible():
            orgalias_list=org.orgalias_list
        else:
            orgalias_list=org.orgalias_list_public

        public = bool(self.current_user)

        orgalias_list = [orgalias.obj(public=public) for orgalias in orgalias_list]

        obj = org.obj(
            public=public,
            orgalias_obj_list=orgalias_list,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'entity_alias.html',
                obj=obj,
                type_title="Organisation",
                type_title_plural="Organisations",
                type_url="organisation",
                type_alias_list="orgalias_list",
                type_li_template="org_li",
                )

    @authenticated
    def post(self, org_id_string):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)

        org = self._get_org(org_id_string)

        orgalias = Orgalias.get(self.orm, name, org, self.current_user, True)
        self.orm.commit()

        self.redirect(self.next or self.url_root[:-1] + org.url)



class OrgListTaskAddressHandler(BaseOrgHandler, BaseOrgtagHandler):
    def get(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("nameSearch", None, json=is_json)
        tag_name_list = self.get_arguments("tag", json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)

        if self.deep_visible():
            address_list_name = "address_list"
        else:
            address_list_name = "address_list_public"

        org_and_alias_list, org_count, geobox, latlon = self._get_org_list_search(
            name=name,
            name_search=name_search,
            tag_name_list=tag_name_list,
            visibility=self.parameters["visibility"],
            geo=False,
            address=False,
            limit=100,
            offset=offset,
            )

        if self.has_geo_arguments():
            offset = None

        org_packet = {
            "org_list": [],
            "org_count": org_count,
            }

        if offset is not None:
            org_packet["offset"] = offset

        for org, alias in org_and_alias_list:
            obj = org.obj(
                public=bool(self.current_user),
                alias=(alias or None)
                )
            org_packet["org_list"].append(obj);

        if self.accept_type("json"):
            self.write_json(org_packet)
        else:
            full_orgtag_list = BaseOrgtagHandler._get_full_orgtag_list(self)
            self.render(
                'organisation_list_task_address.html',
                org_packet=org_packet,
                name_search=name_search,
                tag_name_list=tag_name_list,
                orgtag_list_json=json.dumps(full_orgtag_list),
                )

class OrgListTaskVisibilityHandler(BaseOrgHandler, BaseOrgtagHandler):
    pass
