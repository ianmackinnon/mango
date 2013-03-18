# -*- coding: utf-8 -*-

import json

from base import authenticated, sha1_concat, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from base_note import BaseNoteHandler
from base_org import BaseOrgHandler
from base_event import BaseEventHandler
from orgtag import BaseOrgtagHandler
from address import BaseAddressHandler

from model import Org, Note, Address, Orgalias, Event



class OrgListHandler(BaseOrgHandler, BaseOrgtagHandler,
                       MangoEntityListHandlerMixin):
    @property
    def _create(self):
        return self._create_org

    @property
    def _get(self):
        return self._get_org

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



class OrgNewHandler(BaseOrgHandler):
    @authenticated
    def get(self):
        self.render(
            'organisation.html',
            )



class OrgHandler(BaseOrgHandler, MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_org

    @property
    def _get(self):
        return self._get_org

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
        self.orm_commit()
        self.redirect_next(org.url)



class OrgAddressHandler(BaseOrgHandler, BaseAddressHandler):
    @authenticated
    def put(self, org_id_string, address_id_string):
        org = self._get_org(org_id_string)
        address = self._get_address(address_id_string)
        if address not in org.address_list:
            org.address_list.append(address)
            self.orm_commit()
        self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id_string, address_id_string):
        org = self._get_org(org_id_string)
        address = self._get_address(address_id_string)
        if address in org.address_list:
            org.address_list.remove(address)
            self.orm_commit()
        self.redirect_next(org.url)



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
        self.orm_commit()
        self.redirect_next(org.url)

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



class OrgNoteHandler(BaseOrgHandler, BaseNoteHandler):
    @authenticated
    def put(self, org_id_string, note_id_string):
        org = self._get_org(org_id_string)
        note = self._get_note(note_id_string)
        if note not in org.note_list:
            org.note_list.append(note)
            self.orm_commit()
        self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id_string, note_id_string):
        org = self._get_org(org_id_string)
        note = self._get_note(note_id_string)
        if note in org.note_list:
            org.note_list.remove(note)
            self.orm_commit()
        self.redirect_next(org.url)



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

        del orgtag_list

        # orgtag...

        (orgtag_list, name, name_short, base, base_short, path, search) = \
            self._get_tag_search_args("org_len")

        self.render(
            'entity_tag.html',
            obj=obj,
            tag_list=orgtag_list,
            path=path,
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
            self.orm_commit()
        self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id_string, orgtag_id_string):
        org = self._get_org(org_id_string)
        orgtag = self._get_orgtag(orgtag_id_string)
        if orgtag in org.orgtag_list:
            org.orgtag_list.remove(orgtag)
            self.orm_commit()
        self.redirect_next(org.url)



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
        self.orm_commit()

        self.redirect_next(org.url)



class OrgEventListHandler(BaseOrgHandler, BaseEventHandler):
    @authenticated
    def get(self, org_id_string):

        is_json = self.content_type("application/json")

        # org...

        org = self._get_org(org_id_string)
        
        if self.deep_visible():
            event_list=org.event_list
        else:
            event_list=org.event_list_public
            
        public = bool(self.current_user)

        event_list = [event.obj(public=public) for event in event_list]

        obj = org.obj(
            public=public,
            event_obj_list=event_list,
            )

        del event_list

        # event...

        event_name_search = self.get_argument("search", None, json=is_json)

        event_name_query = BaseEventHandler._get_event_search_query(
            self,
            name_search=event_name_search,
            visibility=self.parameters["visibility"]
            )

        event_list = []
        event_count = event_name_query.count()
        for event in event_name_query[:20]:
            event_list.append(event.obj(
                    public=bool(self.current_user)
                    ))

        self.next = org.url
        self.render(
            'organisation_event.html',
            obj=obj,
            event_list=event_list,
            event_count=event_count,
            search=event_name_search,
            )



class OrgEventHandler(BaseOrgHandler, BaseEventHandler):
    @authenticated
    def put(self, org_id_string, event_id_string):
        org = self._get_org(org_id_string)
        event = self._get_event(event_id_string)
        if event not in org.event_list:
            org.event_list.append(event)
            self.orm_commit()
        self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id_string, event_id_string):
        org = self._get_org(org_id_string)
        event = self._get_event(event_id_string)
        if event in org.event_list:
            org.event_list.remove(event)
            self.orm_commit()
        self.redirect_next(org.url)



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



