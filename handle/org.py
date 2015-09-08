# -*- coding: utf-8 -*-

import json
import random
from collections import OrderedDict

import Levenshtein

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from sqlalchemy.sql.expression import literal_column, or_, and_, not_, distinct
from tornado.web import HTTPError

from base import authenticated, sha1_concat, \
    HistoryEntity, \
    MangoBaseEntityHandlerMixin, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from base_note import BaseNoteHandler
from base_org import BaseOrgHandler
from base_event import BaseEventHandler
from orgtag import BaseOrgtagHandler
from address import BaseAddressHandler
from contact import BaseContactHandler

from base_moderation import \
    get_pending_org_address_id, \
    get_pending_org_contact_id

import geo

from model import Org, Note, Address, Orgalias, Event, Orgtag, Contact, \
    org_orgtag, org_address, org_note

from model_v import Org_v, Address_v, Contact_v, \
    org_address_v, org_contact_v, \
    mango_entity_append_suggestion

from handle.user import \
    get_user_pending_org_address, \
    get_user_pending_org_contact



class OrgListHandler(BaseOrgHandler, BaseOrgtagHandler,
                     MangoEntityListHandlerMixin):
    Entity = Org
    Entity_v = Org_v
    entity_id = "org_id"
    entity_v_id = "org_v_id"

    @property
    def _create(self):
        return self._create_org

    @property
    def _create_v(self):
        return self._create_org_v

    @property
    def _get(self):
        return self._get_org

    @staticmethod
    def _cache_key(name_search, tag_name_list, tag_all, page_view, visibility, moderator):
        if not visibility:
            visibility = "public"
        return sha1_concat(json.dumps({
                "nameSearch": name_search,
                "tag": tuple(set(tag_name_list)),
                "tagAll": tag_all,
                "visibility": visibility,
                "moderator": moderator,
                "pageView": page_view,
                }))

    @staticmethod
    def _get_random_suggestions(results, count=2):
        suggestions = []

        if not (results and count):
            return suggestions

        for i in xrange(count):
            total = 0
            for name, freq in results:
                total += freq

            if not total:
                break

            target = random.randrange(total)
            total = 0
            for i, (name, freq) in enumerate(results):
                total += freq
                if total > target:
                    suggestions.append(results.pop(i)[0])
                    break

        return suggestions

    def _get_tag_suggestions(self, tag_list):
        include = [
            u'exhibitor',
            u'delegate',
            u'market',
            u'activity',
        ]

        results = []
        for path_short in include:
            q = self.orm.query(Orgtag.base_short, func.count(Org.org_id).label("freq")) \
                .join(org_orgtag, org_orgtag.c.orgtag_id==Orgtag.orgtag_id) \
                .join(Org, Org.org_id==org_orgtag.c.org_id) \
                .filter(Orgtag.public==True, Orgtag.virtual==None) \
                .filter(Orgtag.path_short==path_short) \
                .filter(Org.public==True) \
                .group_by(Orgtag.orgtag_id) \
                .order_by(func.count(Org.org_id).desc()) \
                .limit(10)
            
            results += list(q.all())

        return self._get_random_suggestions(results, 2)


    def _get_name_suggestion(self, has_name, count=2):
        suggestions = []
        if has_name:
            return suggestions

        q = self.orm.query(Org.name, func.count(Orgtag.orgtag_id).label("freq")) \
            .join(org_orgtag, org_orgtag.c.org_id==Org.org_id) \
            .join(Orgtag, Orgtag.orgtag_id==org_orgtag.c.orgtag_id) \
            .filter(Org.public==True) \
            .filter(Orgtag.public==True, Orgtag.virtual==None) \
            .group_by(Org.org_id) \
            .order_by(func.count(Orgtag.orgtag_id).desc()) \
            .limit(30)

        results = q.all()

        return self._get_random_suggestions(results, 2)

    def _get_suggestions(self, tag_list, has_name):
        suggestions = {}
        tag = self._get_tag_suggestions(tag_list)
        name = self._get_name_suggestion(has_name)

        if tag:
            suggestions["tag"] = tag
        if name:
            suggestions["name"] = name

        return suggestions

    def get(self):
        is_json = self.content_type("application/json")

        min_radius = 10

        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("nameSearch", None, json=is_json)
        tag_name_list = self.get_arguments_multi("tag", json=is_json)
        tag_all = self.get_argument_bool("tagAll", None, json=is_json)
        location = self.get_argument_geobox(
            "location", min_radius=min_radius, default=None, json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)
        page_view = self.get_argument_allowed(
            "pageView", ["entity", "map", "marker"],
            default="entity", json=is_json)

        if not self.accept_type("json"):
            if self.has_javascript:
                self.load_map = True
                self.render(
                    'organisation-list.html',
                    name=name,
                    name_search=name_search,
                    tag_name_list=tag_name_list,
                    tag_all=tag_all,
                    location=location and location.to_obj(),
                    offset=offset,
                    )
                return;
            if page_view == "entity":
                page_view = "map"

        cache_key = None
        if self.accept_type("json") and not location and not offset:
            cache_key = self._cache_key(
                name_search,
                tag_name_list,
                tag_all,
                page_view,
                self.parameters.get("visibility", None),
                self.moderator,
                )
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
            tag_all=tag_all,
            location=location,
            visibility=self.parameters.get("visibility", None),
            offset=offset,
            page_view=page_view,
            )

        org_packet["hint"] = self._get_suggestions(
            tag_name_list, bool(name or name_search))

        if cache_key:
            self.cache.set(cache_key, json.dumps(org_packet))

        if self.accept_type("json"):
            self.write_json(org_packet)
        else:
            self.load_map = True
            self.render(
                'organisation-list.html',
                org_packet=org_packet,
                name=name,
                name_search=name_search,
                tag_name_list=tag_name_list,
                tag_all=tag_all,
                location=location and location.to_obj(),
                offset=offset,
                )



class OrgNewHandler(BaseOrgHandler):
    @authenticated
    def get(self):
        if self.parameters.get("view", None) != "edit":
            self.next_ = "/organisation"
            self.redirect_next()
            return

        self.render(
            'organisation.html',
            )



class OrgSearchHandler(BaseOrgHandler):
    def get(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        public = not self.moderator

        search = self.orm.get_bind().search

        if search:
            data = {
                "query": {
                    "multi_match": {
                        "fields": [
                            "alias.straight^3",
                            "alias.fuzzy",
                            ],
                        "query": name
                        }
                    }
                }
            if public:
                data = {
                    "query": {
                        "filtered": {
                            "filter": {
                                "term": {
                                    "public": 1
                                    }
                                },
                            "query": {
                                "multi_match": {
                                    "fields": [
                                        "alias.straight^3",
                                        "alias.fuzzy",
                                        ],
                                    "query": name
                                    }
                                }
                            }
                        }
                    }

            results = search.search(data, index="mango", doc_type="org")
            org_list = []
            for hit in results["hits"]["hits"]:
                source = hit["_source"]
                max_ratio = None
                max_alias = None
                for alias in source["alias"]:
                    ratio = Levenshtein.ratio(name.lower(), alias.lower())
                    if max_alias is None or ratio > max_ratio:
                        max_alias = alias
                        max_ratio = ratio
                if max_alias == source["name"]:
                    max_alias = None
                org = {
                    "orgId": source["org_id"],
                    "name": source["name"],
                    "alias": max_alias,
                    "score": hit["_score"],
                    }
                if not public:
                    org["public"] = source["public"]
                org_list.append(org)
            self.write_json(org_list)
            return

        self.write_json(1)
        
        



class OrgHandler(BaseOrgHandler, MangoEntityHandlerMixin):
    @property
    def _create(self):
        return self._create_org

    @property
    def _create_v(self):
        return self._create_org_v

    @property
    def _decline_v(self):
        return self._decline_org_v

    @property
    def _get(self):
        return self._get_org

    @property
    def _get_v(self):
        return self._get_org_v

    @property
    def _touch(self):
        return self._touch_org

    @property
    def _after_accept_new(self):
        return self._after_org_accept_new

    def touch(self, org_id):
        if not self.moderator:
            raise HTTPError(405)

        # Decline (touch) pending child entities

        MangoBaseEntityHandlerMixin._touch_pending_child_entities(
            self, Address, "address_id", "address", org_id,
            get_pending_org_address_id,
            BaseAddressHandler._decline_address_v)

        MangoBaseEntityHandlerMixin._touch_pending_child_entities(
            self, Contact, "contact_id", "contact", org_id,
            get_pending_org_contact_id,
            BaseContactHandler._decline_contact_v)

        return MangoEntityHandlerMixin.touch(self, org_id)

        


    def get(self, org_id):
        note_search, note_order, note_offset = self.get_note_arguments()

        public = self.moderator

        required = True
        org_v = None
        if self.current_user:
            org_v = self._get_org_v(org_id)
            if org_v:
                required = False
        org = self._get_org(org_id, required=required)

        if self.moderator and not org:
            self.next_ = "%s/revision" % org_v.url
            return self.redirect_next()

        if org:
            # We don't need to alter these from now on.
            if self.deep_visible():
                address_list=list(org.address_list)
                orgtag_list=list(org.orgtag_list)
                event_list=list(org.event_list)
                orgalias_list=list(org.orgalias_list)
                contact_list=list(org.contact_list)
            else:
                address_list=list(org.address_list_public)
                orgtag_list=list(org.orgtag_list_public)
                event_list=list(org.event_list_public)
                orgalias_list=list(org.orgalias_list_public)
                contact_list=list(org.contact_list_public)

            note_list, note_count = org.note_list_filtered(
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                all_visible=self.deep_visible(),
                )
        else:
            address_list=[]
            orgtag_list=[]
            event_list=[]
            orgalias_list=[]
            contact_list=[]
            note_list=[]
            note_count = 0

        if self.contributor:
            org_id = org and org.org_id or org_v.org_id

            mango_entity_append_suggestion(
                self.orm, address_list, get_user_pending_org_address,
                self.current_user, org_id, "address_id")

            mango_entity_append_suggestion(
                self.orm, contact_list, get_user_pending_org_contact,
                self.current_user, org_id, "contact_id")

        address_list = [address.obj(public=public) for address in address_list]
        orgtag_list = [orgtag.obj(public=public) for orgtag in orgtag_list]
        note_list = [note.obj(public=public) for note in note_list]
        event_list = [event.obj(public=public) for event in event_list]
        orgalias_list = [orgalias.obj(public=public) for orgalias in orgalias_list]
        contact_list = [contact.obj(public=public, medium=contact.medium.name) for contact in contact_list]

        edit_block = False
        if org_v:
            if self.contributor:
                org = org_v
            else:
                edit_block = True

        obj = org.obj(
            public=public,
            address_list=address_list,
            orgtag_list=orgtag_list,
            note_list=note_list,
            note_count=note_count,
            event_list=event_list,
            orgalias_list=orgalias_list,
            contact_list=contact_list,
            )

        version_url=None
        if self.current_user and self._count_org_history(org_id) > 1:
            version_url="%s/revision" % org.url

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.load_map = True
            self.render(
                'organisation.html',
                obj=obj,
                edit_block=edit_block,
                note_search=note_search,
                note_order=note_order,
                note_offset=note_offset,
                version_url=version_url,
                )
        


class OrgRevisionListHandler(BaseOrgHandler):
    @authenticated
    def get(self, org_id):
        org_v_list, org = self._get_org_history(org_id)

        history = []
        for org_v in org_v_list:
            user = org_v.moderation_user

            is_latest = False
            if self.moderator:
                if org and org.a_time == org_v.a_time:
                    is_latest = True
            else:
                if not history:
                    is_latest = True

            entity = HistoryEntity(
                type="organisation",
                entity_id=org_v.org_id,
                entity_v_id=org_v.org_v_id,
                date=org_v.a_time,
                existence=bool(org),
                existence_v=org_v.existence,
                is_latest=is_latest,
                public=org_v.public,
                name=org_v.name,
                user_id=user.user_id,
                user_name=user.name,
                user_moderator=user.moderator,
                gravatar_hash=user.gravatar_hash(),
                url=org_v.url,
                url_v=org_v.url_v,
                )
            history.append(entity)

        if not history:
            raise HTTPError(404, "%s: No such org" % (org_id))

        if not self.moderator:
            if len(history) == int(bool(org)):
                raise HTTPError(404)
        
        version_current_url = (org and org.url) or (not self.moderator and history and history[-1].url)

        self.load_map = True
        self.render(
            'revision-history.html',
            entity=True,
            version_current_url=version_current_url,
            latest_a_time=org and org.a_time,
            title_text="Revision History",
            history=history,
            )
        


class OrgRevisionHandler(BaseOrgHandler):
    def _get_org_revision(self, org_id, org_v_id):
        query = self.orm.query(Org_v) \
            .filter_by(org_id=org_id) \
            .filter_by(org_v_id=org_v_id)

        try:
            org_v = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d:%d: No such org revision" % (org_id, org_v_id))

        query = self.orm.query(Org) \
            .filter_by(org_id=org_id)

        try:
            org = query.one()
        except NoResultFound:
            org = None

        return org_v, org

    @authenticated
    def get(self, org_id, org_v_id):
        org_v, org = self._get_org_revision(org_id, org_v_id)

        if not org_v.existence:
            raise HTTPError(404)

        if self.moderator:
            if org and org.a_time == org_v.a_time:
                self.next_ = org.url
                return self.redirect_next()
        else:
            if not ((org_v.moderation_user == self.current_user) or \
                        (org and org_v.a_time == org.a_time)):
                raise HTTPError(404)
            newest_org_v = self.orm.query(Org_v) \
                .filter_by(moderation_user=self.current_user) \
                .order_by(Org_v.org_v_id.desc()) \
                .first()
            if not newest_org_v:
                raise HTTPError(404)
            latest_a_time = self._get_org_latest_a_time(org_id)
            if latest_a_time and org_v.a_time < latest_a_time:
                raise HTTPError(404)
            if org and newest_org_v.a_time < org.a_time:
                raise HTTPError(404)
            if newest_org_v == org_v:
                self.next_ = org_v.url
                return self.redirect_next()
            org = newest_org_v

        obj = org and org.obj(
            public=True,
            )

        obj_v = org_v.obj(
            public=True,
            )

        fields = (
            ("name", "name"),
            ("description", "markdown"),
            ("end_date", "date"),
            ("public", "public")
            )

        latest_a_time = self._get_org_latest_a_time(org_id)

        self.render(
            'revision.html',
            action_url=org_v.url,
            version_url="%s/revision" % (org_v.url),
            version_current_url=org and org.url,
            latest_a_time=latest_a_time,
            fields=fields,
            obj=obj,
            obj_v=obj_v,
            )
        


class OrgAddressListHandler(BaseOrgHandler, BaseAddressHandler):
    @authenticated
    def get(self, org_id):
        required = True
        if self.contributor:
            org_v = self._get_org_v(org_id)
            if org_v:
                required = False
        org = self._get_org(org_id, required=required)

        if not self.moderator and org_v:
            org = org_v

        obj = org.obj(
            public=self.moderator,
            )

        self.load_map = True
        self.render(
            'address.html',
            obj=None,
            entity=obj,
            )
        
    @authenticated
    def post(self, org_id):
        required = True
        if self.contributor:
            org_v = self._get_org_v(org_id)
            if org_v:
                required = False
        org = self._get_org(org_id, required=required)

        # Fix MySQL autoincrement reset
        self._update_entity_autoincrement(
            Address, Address_v, "address_id")

        address = self._create_address()
        self._before_address_set(address)
        self.orm.add(address)
        self.orm_commit()
        if self.moderator:
            org.address_list.append(address)
            self.orm_commit()
            return self.redirect_next(org.url)

        id_ = address.address_id

        self.orm.delete(address)
        self.orm_commit()

        self.orm.query(Address_v) \
            .filter(Address_v.address_id==id_) \
            .delete()
        self.orm_commit()

        address_v = self._create_address_v(id_)
        self._before_address_set(address_v)
        self.orm.add(address_v)
        self.orm_commit()

        org_id = org and org.org_id or org_v.org_id
        address_id = id_

        engine = self.orm.connection().engine
        sql = """
insert into org_address_v (org_id, address_id, a_time, existence)
values (%d, %d, 0, 1)""" % (org_id, address_id)
        engine.execute(sql)

        return self.redirect_next(address_v.url)



class OrgAddressHandler(BaseOrgHandler, BaseAddressHandler):
    @authenticated
    def put(self, org_id, address_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        address = self._get_address(address_id)
        if address not in org.address_list:
            org.address_list.append(address)
            self.orm_commit()
        return self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id, address_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        address = self._get_address(address_id)
        if address in org.address_list:
            org.address_list.remove(address)
            self.orm_commit()
        return self.redirect_next(org.url)



class OrgContactListHandler(BaseOrgHandler, BaseContactHandler):
    @authenticated
    def get(self, org_id):
        required = True
        if self.contributor:
            org_v = self._get_org_v(org_id)
            if org_v:
                required = False
        org = self._get_org(org_id, required=required)

        if not self.moderator and org_v:
            org = org_v

        obj = org.obj(
            public=self.moderator,
            )

        self.render(
            'contact.html',
            obj=None,
            entity=obj,
            medium_list=self.medium_list,
            )
        
    @authenticated
    def post(self, org_id):
        required = True
        if self.contributor:
            org_v = self._get_org_v(org_id)
            if org_v:
                required = False
        org = self._get_org(org_id, required=required)

        # Fix MySQL autoincrement reset
        self._update_entity_autoincrement(
            Contact, Contact_v, "contact_id")

        contact = self._create_contact()
        self._before_contact_set(contact)
        self.orm.add(contact)
        self.orm_commit()
        if self.moderator:
            org.contact_list.append(contact)
            self.orm_commit()
            return self.redirect_next(org.url)

        id_ = contact.contact_id

        self.orm.delete(contact)
        self.orm_commit()

        self.orm.query(Contact_v) \
            .filter(Contact_v.contact_id==id_) \
            .delete()
        self.orm_commit()

        contact_v = self._create_contact_v(id_)
        self._before_contact_set(contact_v)
        self.orm.add(contact_v)
        self.orm_commit()

        org_id = org and org.org_id or org_v.org_id
        contact_id = id_

        engine = self.orm.connection().engine
        sql = """
insert into org_contact_v (org_id, contact_id, a_time, existence)
values (%d, %d, 0, 1)""" % (org_id, contact_id)
        engine.execute(sql)

        return self.redirect_next(contact_v.url)



class OrgContactHandler(BaseOrgHandler, BaseContactHandler):
    @authenticated
    def put(self, org_id, contact_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        contact = self._get_contact(contact_id)
        if contact not in org.contact_list:
            org.contact_list.append(contact)
            self.orm_commit()
        return self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id, contact_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        contact = self._get_contact(contact_id)
        if contact in org.contact_list:
            org.contact_list.remove(contact)
            self.orm_commit()
        return self.redirect_next(org.url)



class OrgNoteListHandler(BaseOrgHandler, BaseNoteHandler):
    @authenticated
    def post(self, org_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        note = self._create_note()

        org.note_list.append(note)
        self.orm_commit()
        return self.redirect_next(org.url)

    @authenticated
    def get(self, org_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        obj = org.obj(
            public=self.moderator,
            )
        self.next_ = org.url
        self.render(
            'note.html',
            entity=obj
            )



class OrgNoteHandler(BaseOrgHandler, BaseNoteHandler):
    @authenticated
    def put(self, org_id, note_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        note = self._get_note(note_id)
        if note not in org.note_list:
            org.note_list.append(note)
            self.orm_commit()
        return self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id, note_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        note = self._get_note(note_id)
        if note in org.note_list:
            org.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(org.url)



class OrgOrgtagListHandler(BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def post(self, org_id):
        if not self.moderator:
            raise HTTPError(404)

        is_json = self.content_type("application/json")
        group = self.get_argument("group", None, json=is_json)
        tag_id_list = self.get_arguments_int("tag")

        org = self._get_org(org_id)

        if not group:
            raise HTTPError(404)

        group_tag_query = self.orm.query(Orgtag) \
            .filter_by(path_short=group) \
            .order_by(Orgtag.base_short)

        for tag in group_tag_query:
            if tag.orgtag_id not in tag_id_list:
                while tag in org.orgtag_list:
                    org.orgtag_list.remove(tag)
            if tag.orgtag_id in tag_id_list and tag not in org.orgtag_list:
                org.orgtag_list.append(tag)
                
        if group_tag_query:
            self.orm_commit()

        return self.redirect(self.url_rewrite(self.request.uri))

    @authenticated
    def get(self, org_id):
        if not self.moderator:
            raise HTTPError(404)

        is_json = self.content_type("application/json")
        group = self.get_argument("group", None, json=is_json)

        # org...

        org = self._get_org(org_id)

        if self.deep_visible():
            orgtag_list=org.orgtag_list
        else:
            orgtag_list=org.orgtag_list_public

        public = self.moderator

        orgtag_list = [orgtag.obj(public=public) for orgtag in orgtag_list]

        obj = org.obj(
            public=public,
            orgtag_list=orgtag_list,
            )

        del orgtag_list

        # orgtag...

        (orgtag_list, name, name_short, base, base_short,
         path, search, sort) = self._get_tag_search_args()

        group_tag_list = []
        if group:
            group_tag_query = self.orm.query(Orgtag) \
                .filter_by(path_short=group) \
                .order_by(Orgtag.base_short)
            group_tag_list = [orgtag.obj() for orgtag in group_tag_query]

        path_query = self.orm.query(Orgtag.path, Orgtag.path_short) \
            .filter(Orgtag.path!=None) \
            .group_by(Orgtag.path_short)
        path_list = list(path_query)

        self.render(
            'entity-tag.html',
            obj=obj,
            tag_list=orgtag_list,
            path=path,
            search=search,
            sort=sort,
            type_title="Company",
            type_title_plural="Companies",
            type_url="organisation",
            type_tag_list="orgtagList",
            type_entity_list="org_list",
            type_li_template="org_li",
            type_length="org_len",
            path_list=path_list,
            group=group,
            group_tag_list=group_tag_list,
            )



class OrgOrgtagHandler(BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def put(self, org_id, orgtag_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        orgtag = self._get_tag(orgtag_id)
        if orgtag not in org.orgtag_list:
            org.orgtag_list.append(orgtag)
            self.orm_commit()
        return self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id, orgtag_id):
        if not self.moderator:
            raise HTTPError(404)

        org = self._get_org(org_id)
        orgtag = self._get_tag(orgtag_id)
        if orgtag in org.orgtag_list:
            org.orgtag_list.remove(orgtag)
            self.orm_commit()
        return self.redirect_next(org.url)



class OrgOrgaliasListHandler(BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def get(self, org_id):
        if not self.moderator:
            raise HTTPError(404)

        # org...

        org = self._get_org(org_id)

        if self.parameters.get("view", None) != "edit":
            self.next_ = org.url
            self.redirect_next()

        if self.deep_visible():
            orgalias_list=org.orgalias_list
        else:
            orgalias_list=org.orgalias_list_public

        public = self.moderator

        orgalias_list = [orgalias.obj(public=public) for orgalias in orgalias_list]

        obj = org.obj(
            public=public,
            orgalias_list=orgalias_list,
            )

        if self.accept_type("json"):
            self.write_json(obj)
        else:
            self.render(
                'entity-alias.html',
                obj=obj,
                type_title="Company",
                type_title_plural="Companies",
                type_url="organisation",
                type_alias_list="orgaliasList",
                type_li_template="org_li",
                )

    @authenticated
    def post(self, org_id):
        if not self.moderator:
            raise HTTPError(404)
            
        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)

        org = self._get_org(org_id)

        orgalias = Orgalias.get(self.orm, name, org, self.current_user, True)
        self.orm_commit()

        return self.redirect_next(org.url)



class OrgEventListHandler(BaseOrgHandler, BaseEventHandler):
    @authenticated
    def get(self, org_id):
        if not self.moderator:
            raise HTTPError(404)
            
        is_json = self.content_type("application/json")

        # org...

        org = self._get_org(org_id)
        
        if self.deep_visible():
            event_list=org.event_list
        else:
            event_list=org.event_list_public
            
        public = self.moderator

        event_list = [event.obj(public=public) for event in event_list]

        obj = org.obj(
            public=public,
            event_list=event_list,
            )

        del event_list

        # event...

        event_name_search = self.get_argument("search", None, json=is_json)

        event_name_query = BaseEventHandler._get_event_search_query(
            self,
            name_search=event_name_search,
            visibility=self.parameters.get("visibility", None),
            )

        event_list = []
        event_count = event_name_query.count()
        for event in event_name_query[:20]:
            event_list.append(event.obj(
                    public=public,
                    ))

        self.next_ = org.url
        self.render(
            'organisation-event.html',
            obj=obj,
            event_list=event_list,
            event_count=event_count,
            search=event_name_search,
            )



class OrgEventHandler(BaseOrgHandler, BaseEventHandler):
    @authenticated
    def put(self, org_id, event_id):
        if not self.moderator:
            raise HTTPError(404)
            
        org = self._get_org(org_id)
        event = self._get_event(event_id)
        if event not in org.event_list:
            org.event_list.append(event)
            self.orm_commit()
        return self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id, event_id):
        if not self.moderator:
            raise HTTPError(404)
            
        org = self._get_org(org_id)
        event = self._get_event(event_id)
        if event in org.event_list:
            org.event_list.remove(event)
            self.orm_commit()
        return self.redirect_next(org.url)



class ModerationOrgDescHandler(BaseOrgHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        is_json = self.content_type("application/json")

        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("nameSearch", None, json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)

        name_subquery = self._get_name_search_query(
            name=None,
            name_search=None,
            visibility=self.parameters.get("visibility", None),
            ).subquery()

        org_alias_query = self.orm.query(Org, Orgalias) \
            .join(name_subquery, Org.org_id==name_subquery.c.org_id) \
            .outerjoin(Orgalias, Orgalias.orgalias_id==name_subquery.c.orgalias_id)
        

        org_alias_query = org_alias_query.filter(Org.description != None)
 
        org_packet = {
            }
        
        orgs = OrderedDict()
        for org, alias in org_alias_query:
            if not org.org_id in orgs:
                orgs[org.org_id] = {
                    "org": org,
                    "alias": alias and alias.name,
                    }
                
        org_packet["orgList"] = []
        for org_id, data in orgs.items():
            org = data["org"]
            org_packet["orgList"].append(org.obj(
                    alias=data["alias"],
                    public=self.moderator,
                    ))

        self.render(
            'moderation-org-desc.html',
            org_packet=org_packet,
            name=name,
            name_search=name_search,
            offset=offset,
            )



class ModerationOrgIncludeHandler(BaseOrgHandler):
    @authenticated
    def get(self):
        if not self.moderator:
            raise HTTPError(404)

        is_json = self.content_type("application/json")

        org_list = self.orm.query(Org) \
            .limit(10)

        act_query = self.orm.query(func.count(Orgtag.orgtag_id).label("count")) \
            .join(org_orgtag) \
            .add_columns(org_orgtag.c.org_id) \
            .filter(or_(
                Orgtag.path_short==u'activity',
                Orgtag.path_short==u'activity-exclusion',
                )) \
            .group_by(org_orgtag.c.org_id) \
            .subquery()

        addr_query = self.orm.query(func.count(Address.address_id).label("count")) \
            .join(org_address) \
            .add_columns(org_address.c.org_id) \
            .filter(Address.public==True) \
            .group_by(org_address.c.org_id) \
            .subquery()

        dseitag_query = self.orm.query(func.count(Orgtag.orgtag_id) \
                                    .label("count")) \
            .join(org_orgtag) \
            .add_columns(org_orgtag.c.org_id) \
            .filter(Orgtag.name_short.startswith(
                u"products-and-services|dsei%")) \
            .group_by(org_orgtag.c.org_id) \
            .subquery()

        saptag_query = self.orm.query(func.count(Orgtag.orgtag_id) \
                                   .label("count")) \
            .join(org_orgtag) \
            .add_columns(org_orgtag.c.org_id) \
            .filter(Orgtag.name_short.startswith(
                u"products-and-services|security%")) \
            .group_by(org_orgtag.c.org_id) \
            .subquery()

        tag_query = self.orm.query(func.count(Orgtag.orgtag_id) \
                                   .label("count")) \
            .join(org_orgtag) \
            .add_columns(org_orgtag.c.org_id) \
            .filter(not_(Orgtag.name_short.startswith(
                u"products-and-services%"))) \
            .group_by(org_orgtag.c.org_id) \
            .subquery()

        dsei2015_query = self.orm.query(func.count(Orgtag.orgtag_id) \
                                       .label("count")) \
            .join(org_orgtag) \
            .add_columns(org_orgtag.c.org_id) \
            .filter(Orgtag.name_short==u"exhibitor|dsei-2015") \
            .group_by(org_orgtag.c.org_id) \
            .subquery()

        uk_south = 49.87
        uk_north = 55.81
        uk_west = -6.38
        uk_east = 1.77
        in_uk_or_no_address = or_(
                and_(
                    Address.latitude != None,
                    Address.longitude != None,
                    Address.latitude >= uk_south,
                    Address.latitude <= uk_north,
                    Address.longitude >= uk_west,
                    Address.longitude <= uk_east,
                ),
                Address.latitude == None,
            )
        # .filter(in_uk_or_no_address) \

        israel_query = self.orm.query(func.count(Orgtag.orgtag_id) \
                                     .label("count")) \
            .join(org_orgtag) \
            .add_columns(org_orgtag.c.org_id) \
            .filter(Orgtag.name_short==u"market|military-export-applicant-to-israel") \
            .group_by(org_orgtag.c.org_id) \
            .subquery()

        sipri_query = self.orm.query(func.count(Orgtag.orgtag_id) \
                                     .label("count")) \
            .join(org_orgtag) \
            .add_columns(org_orgtag.c.org_id) \
            .filter(Orgtag.name_short.startswith(
                u"products-and-services|sipri%")) \
            .group_by(org_orgtag.c.org_id) \
            .subquery()

        note_query = self.orm.query(func.count(Note.note_id) \
                                     .label("count")) \
            .join(org_note) \
            .add_columns(org_note.c.org_id) \
            .group_by(org_note.c.org_id) \
            .subquery()

        def location_subquery(location, min_radius=16):  # 10 miles
            location = geo.bounds(location, min_radius=min_radius)
            return self.orm.query(func.count(Address.address_id) \
                                           .label("count")) \
                .join(org_address) \
                .add_columns(org_address.c.org_id) \
                .filter(and_(
                    Address.latitude != None,
                    Address.longitude != None,
                    Address.latitude >= location.south,
                    Address.latitude <= location.north,
                    Address.longitude >= location.west,
                    Address.longitude <= location.east,
                )) \
                .group_by(org_address.c.org_id) \
                .subquery()

        canterbury_query = location_subquery(u"canterbury")

        exist_clause = "exists (select 1 from org_include where org_include.org_id = org.org_id)"

        org_query = self.orm.query(Org) \
            .outerjoin(act_query, act_query.c.org_id==Org.org_id) \
            .outerjoin(addr_query, addr_query.c.org_id==Org.org_id) \
            .outerjoin(dseitag_query, dseitag_query.c.org_id==Org.org_id) \
            .outerjoin(saptag_query, saptag_query.c.org_id==Org.org_id) \
            .outerjoin(tag_query, tag_query.c.org_id==Org.org_id) \
            .outerjoin(dsei2015_query, dsei2015_query.c.org_id==Org.org_id) \
            .outerjoin(israel_query, israel_query.c.org_id==Org.org_id) \
            .outerjoin(canterbury_query, canterbury_query.c.org_id==Org.org_id) \
            .outerjoin(sipri_query, sipri_query.c.org_id==Org.org_id) \
            .outerjoin(note_query, note_query.c.org_id==Org.org_id) \
            .add_columns(
                literal_column(exist_clause).label("include"),
                func.coalesce(act_query.c.count, 0).label("act"),
                func.coalesce(addr_query.c.count, 0).label("addr"),
                func.coalesce(dseitag_query.c.count, 0).label("dseitag"),
                func.coalesce(saptag_query.c.count, 0).label("saptag"),
                func.coalesce(tag_query.c.count, 0).label("tag"),
                func.coalesce(dsei2015_query.c.count, 0).label("dsei2015"),
                func.coalesce(israel_query.c.count, 0).label("israel"),
                func.coalesce(canterbury_query.c.count, 0).label("canterbury"),
                func.coalesce(sipri_query.c.count, 0).label("sipri"),
                func.coalesce(note_query.c.count, 0).label("note"),
                ) \
            .filter(Org.end_date==None) \
            .order_by(
                literal_column(u"((dseitag > 0) * 4 + (saptag > 0) * 2 + (sipri > 0))").desc(),
                literal_column(u"tag").desc(),
                Org.name,
            )

        packet = {
            "act_include_public": 0,
            "act_exclude_public": [],
            "act_include_private": [],
            "act_exclude_private": 0,
            "act_include_pending": [],
            "act_exclude_pending": [],

            "addr_public": [],

            "remove_public": [],
            "remove_private": [],

            "desc_pending": [],
            "dsei2015_pending": [],
            "israel_pending": [],
            "canterbury_pending": [],
            "sipri_pending": [],
            "note_pending": [],
            "include_pending": [],

            "exclude_pending": 0,
            }

        for org, include, act, addr, dseitag, saptag, tag, dsei2015, israel, canterbury, sipri, note in org_query:
            if act:
                if org.public:
                    if not addr:
                        packet["addr_public"] \
                            .append((org, dseitag, saptag, tag))
                    elif include:
                        packet["act_include_public"] += 1
                    else:
                        packet["act_exclude_public"] \
                            .append((org, dseitag, saptag, tag))
                elif org.public == False:
                    if not include:
                        packet["act_exclude_private"] += 1
                    else:
                        packet["act_include_private"] \
                            .append((org, dseitag, saptag, tag))
                else:
                    if not include:
                        packet["act_exclude_pending"] \
                            .append((org, dseitag, saptag, tag))
                    else:
                        packet["act_include_pending"] \
                            .append((org, dseitag, saptag, tag))
            elif org.public:
                packet["remove_public"] \
                    .append((org, dseitag, saptag, tag))
            elif org.public == False:
                    packet["remove_private"] \
                        .append((org, dseitag, saptag, tag))
            else:
                # Pending
                if org.description:
                    packet["desc_pending"] \
                        .append((org, dseitag, saptag, tag))
                elif note > 3:
                    packet["note_pending"] \
                        .append((org, dseitag, saptag, tag))
                elif dsei2015:
                    packet["dsei2015_pending"] \
                        .append((org, dseitag, saptag, tag))
                elif israel:
                    packet["israel_pending"] \
                        .append((org, dseitag, saptag, tag))
                elif canterbury:
                    packet["canterbury_pending"] \
                        .append((org, dseitag, saptag, tag))
                elif sipri:
                    packet["sipri_pending"] \
                        .append((org, dseitag, saptag, tag))
                elif include:
                    packet["include_pending"] \
                        .append((org, dseitag, saptag, tag))
                else:
                    packet["exclude_pending"] += 1

        self.render(
            'moderation-org-include.html',
            packet=packet,
            max_block_length=200
            )
