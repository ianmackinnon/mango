# -*- coding: utf-8 -*-

import json

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import exists
from tornado.web import HTTPError

from base import BaseHandler, authenticated
from note import BaseNoteHandler
from orgtag import BaseOrgtagHandler
from address import BaseAddressHandler

from model import Org, Note, Address, Orgtag, org_orgtag, org_address



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

    def _get_org_list_search(self, name=None, name_search=None,
                             tag_name_list=None, visibility=None,
                             address_list_name=None, geo=True, address=True, limit=10, offset=0):
        org_list = self.orm.query(Org)

        org_list = self.filter_visibility(org_list, Org, visibility)

        if name:
            org_list = org_list.filter_by(name=name)
        elif name_search:
            org_list = org_list\
                .filter(Org.name.contains(name_search))

        if tag_name_list:
            org_list = org_list.join((Orgtag, Org.orgtag_list)) \
                .filter(Orgtag.short.in_(tag_name_list))

        if address:
            assert address_list_name in [
                "address_list",
                "address_list_public",
                ]
            
            org_list = org_list \
                .outerjoin((Address, getattr(Org, address_list_name))) \
                .options(joinedload(address_list_name))
        else:
            org_list = org_list \
                .filter(~exists().where(org_address.c.org_id == Org.org_id))

        geobox = None
        latlon = None
        if address and geo and self.has_geo_arguments():
            org_list, geobox, latlon = self.filter_geo(org_list, limit)
            org_list = org_list.all()
            org_count = len(org_list)
        else:
            if name_search:
                org_list = org_list \
                    .order_by(Org.name.startswith(name_search).desc(), Org.name)
            else:
                org_list = org_list.order_by(Org.name)
            org_count = self.orm.query(org_list.subquery().c.org_id.distinct()).count()
            if offset:
                org_list = org_list.offset(offset);
            if limit:
                org_list = org_list.limit(limit)
            org_list = org_list.all()

        return org_list, org_count, geobox, latlon
    


class OrgListHandler(BaseOrgHandler, BaseOrgtagHandler):
    def get(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("name_search", None, json=is_json)
        tag_name_list = self.get_arguments("tag", json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)

        if self.deep_visible():
            address_list_name = "address_list"
        else:
            address_list_name = "address_list_public"

        org_list, org_count, geobox, latlon = self._get_org_list_search(
            name=name,
            name_search=name_search,
            tag_name_list=tag_name_list,
            visibility=self.parameters["visibility"],
            address_list_name=address_list_name,
            offset=offset,
            )

        if self.has_geo_arguments():
            offset = None

        org_packet = {
            "org_list": [],
            "org_count": org_count,
            "geobox": geobox,
            "latlon": latlon,
            }

        if offset is not None:
            org_packet["offset"] = offset

        for org in org_list:
            if self.deep_visible():
                address_list = org.address_list
            else:
                address_list = org.address_list_public
            address_list = [address.obj(public=bool(self.current_user)) \
                                for address in address_list]
            obj = org.obj(
                public=bool(self.current_user),
                address_obj_list=address_list,
                )
            org_packet["org_list"].append(obj);

        if self.accept_type("json"):
            self.write_json(org_packet)
        else:
            full_orgtag_list = BaseOrgtagHandler._get_full_orgtag_list(self)
            self.render(
                'organisation_list.html',
                org_packet=org_packet,
                name_search=name_search,
                tag_name_list=tag_name_list,
                lookup=self.lookup,
                orgtag_list_json=json.dumps(full_orgtag_list),
                )

    def post(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)
        public = self.get_argument_public("public", json=is_json)

        org = Org(name, moderation_user=self.current_user, public=public)
        self.orm.add(org)
        self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)



class OrgNewHandler(BaseOrgHandler):
    def get(self):
        self.render(
            'organisation.html',
            )



class OrgHandler(BaseOrgHandler):
    def get(self, org_id_string):
        note_search = self.get_argument("note_search", None)
        note_order = self.get_argument_order("note_order", None)

        public = bool(self.current_user)

        if self.deep_visible():
            options = (
                joinedload("address_list"),
                joinedload("orgtag_list"),
                joinedload("note_list"),
                joinedload("event_list"),
                )
        else:
            options = (
                joinedload("address_list_public"),
                joinedload("orgtag_list_public"),
                joinedload("note_list_public"),
                joinedload("event_list_public"),
                )

        org = self._get_org(org_id_string, options=options)

        if self.deep_visible():
            address_list=org.address_list
            orgtag_list=org.orgtag_list
            note_list=org.note_list
            event_list=org.event_list
        else:
            address_list=org.address_list_public
            orgtag_list=org.orgtag_list_public
            note_list=org.note_list_public
            event_list=org.event_list_public

        address_list = [address.obj(public=public) for address in address_list]
        orgtag_list = [orgtag.obj(public=public) for orgtag in orgtag_list]
        note_list = [note.obj(public=public) for note in note_list]
        event_list = [event.obj(public=public) for event in event_list]

        obj = org.obj(
            public=public,
            address_obj_list=address_list,
            orgtag_obj_list=orgtag_list,
            note_obj_list=note_list,
            event_obj_list=event_list,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'organisation.html',
                obj=obj,
                note_search=note_search,
                note_order=note_order,
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

        if self.deep_visible():
            options = (
                joinedload("orgtag_list"),
                )
        else:
            options = (
                joinedload("orgtag_list_public"),
                )

        org = self._get_org(org_id_string, options=options)

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
        print self.next
        self.redirect(self.next or self.url_root[:-1] + org.url)

    @authenticated
    def delete(self, org_id_string, orgtag_id_string):
        org = self._get_org(org_id_string)
        orgtag = self._get_orgtag(orgtag_id_string)
        if orgtag in org.orgtag_list:
            org.orgtag_list.remove(orgtag)
            self.orm.commit()
        self.redirect(self.next or self.url_root[:-1] + org.url)





class OrgListTaskAddressHandler(BaseOrgHandler, BaseOrgtagHandler):
    def get(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("name_search", None, json=is_json)
        tag_name_list = self.get_arguments("tag", json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)

        if self.deep_visible():
            address_list_name = "address_list"
        else:
            address_list_name = "address_list_public"

        org_list, org_count, geobox, latlon = self._get_org_list_search(
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

        for org in org_list:
            obj = org.obj(
                public=bool(self.current_user),
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
