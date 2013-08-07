# -*- coding: utf-8 -*-

import json

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import exists, or_, and_
from tornado.web import HTTPError

from base import authenticated, sha1_concat, \
    HistoryEntity, \
    MangoEntityHandlerMixin, MangoEntityListHandlerMixin
from base_note import BaseNoteHandler
from base_org import BaseOrgHandler
from base_event import BaseEventHandler
from orgtag import BaseOrgtagHandler
from address import BaseAddressHandler

from model import Org, Note, Address, Orgalias, Event

from model_v import Org_v, Address_v, \
    org_address_v

from handle.user import get_user_pending_org_address



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
    def _cache_key(name_search, tag_name_list, tag_all, page_view, visibility):
        if not visibility:
            visibility = "public"
        return sha1_concat(json.dumps({
                "nameSearch": name_search,
                "tag": tuple(set(tag_name_list)),
                "tagAll": tag_all,
                "visibility": visibility,
                "pageView": page_view,
                }))
    
    def get(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, json=is_json)
        name_search = self.get_argument("nameSearch", None, json=is_json)
        tag_name_list = self.get_arguments_multi("tag", json=is_json)
        tag_all = self.get_argument_bool("tagAll", None, json=is_json)
        location = self.get_argument_geobox("location", None, json=is_json)
        offset = self.get_argument_int("offset", None, json=is_json)
        page_view = self.get_argument_allowed(
            "pageView", ["entity", "map", "marker"],
            default="entity", json=is_json)

        if self.has_javascript and not self.accept_type("json"):
            self.render(
                'organisation_list.html',
                name=name,
                name_search=name_search,
                tag_name_list=tag_name_list,
                tag_all=tag_all,
                location=location and location.to_obj(),
                offset=offset,
                )
            return;

        cache_key = None
        if self.accept_type("json") and not location and not offset:
            cache_key = self._cache_key(
                name_search,
                tag_name_list,
                tag_all,
                page_view,
                self.parameters.get("visibility", None),
                )
            value = self.cache.get(cache_key)
            if value:
                self.set_header("Content-Type", "application/json; charset=UTF-8")
                self.write(value)
                self.finish()
                return

        if not self.accept_type("json"):
            page_view = "map"

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
                tag_all=tag_all,
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
    def _after_accept_new(self):
        return self._after_org_accept_new

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
            self.next = "%s/revision" % org_v.url
            return self.redirect_next()

        if org:
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
        else:
            address_list=[]
            orgtag_list=[]
            event_list=[]
            orgalias_list=[]
            note_list=[]
            note_count = 0

        if self.contributor:
            org_id = org and org.org_id or org_v.org_id

            if org_v:
                # This current shows contributers all the deleted, pending and private addresses that have been added to their pending organisation
                query = self.orm.query(Address) \
                    .filter(exists().where(and_(
                            org_address_v.c.org_id == org_id,
                            org_address_v.c.address_id == Address.address_id,
                            )))
                for address in query.all():
                    address_list.append(address)

            for address_v in get_user_pending_org_address(
                self.orm, self.current_user, org_id):
                
                for i, address in enumerate(address_list):
                    if address.address_id == address_v.address_id:
                        address_list[i] = address_v
                        break
                else:
                    address_list.append(address_v)

        address_list = [address.obj(public=public) for address in address_list]
        orgtag_list = [orgtag.obj(public=public) for orgtag in orgtag_list]
        note_list = [note.obj(public=public) for note in note_list]
        event_list = [event.obj(public=public) for event in event_list]
        orgalias_list = [orgalias.obj(public=public) for orgalias in orgalias_list]

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
            )

        version_url=None
        if self.current_user and self._count_org_history(org_id) > 1:
            version_url="%s/revision" % org.url

        if self.accept_type("json"):
            self.write_json(obj)
        else:
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
                self.next = org.url
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
                self.next = org_v.url
                return self.redirect_next()
            org = newest_org_v

        obj = org and org.obj(
            public=True,
            )

        obj_v = org_v.obj(
            public=True,
            )

        ignore_list = []
        fields = (
            ("name", "name"),
            ("description", "markdown"),
            ("public", "public")
            )

        if not self.moderator or not org_v.moderation_user.moderator:
            ignore_list.append(
                "public"
                )

        latest_a_time = self._get_org_latest_a_time(org_id)

        self.render(
            'revision.html',
            action_url=org_v.url,
            version_url="%s/revision" % (org_v.url),
            version_current_url=org and org.url,
            latest_a_time=latest_a_time,
            fields=fields,
            ignore_list=ignore_list,
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
            raise HTTPError(405)

        org = self._get_org(org_id)
        address = self._get_address(address_id)
        if address not in org.address_list:
            org.address_list.append(address)
            self.orm_commit()
        return self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id, address_id):
        if not self.moderator:
            raise HTTPError(405)

        org = self._get_org(org_id)
        address = self._get_address(address_id)
        if address in org.address_list:
            org.address_list.remove(address)
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
        self.next = org.url
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
            raise HTTPError(405)

        org = self._get_org(org_id)
        note = self._get_note(note_id)
        if note in org.note_list:
            org.note_list.remove(note)
            self.orm_commit()
        return self.redirect_next(org.url)



class OrgOrgtagListHandler(BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def get(self, org_id):
        if not self.moderator:
            raise HTTPError(404)

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

        (orgtag_list, name, name_short, base, base_short, path, search) = \
            self._get_tag_search_args("org_len")

        self.render(
            'entity_tag.html',
            obj=obj,
            tag_list=orgtag_list,
            path=path,
            search=search,
            type_title="Company",
            type_title_plural="Companies",
            type_url="organisation",
            type_tag_list="orgtag_list",
            type_entity_list="org_list",
            type_li_template="org_li",
            type_length="org_len",
            )



class OrgOrgtagHandler(BaseOrgHandler, BaseOrgtagHandler):
    @authenticated
    def put(self, org_id, orgtag_id):
        if not self.moderator:
            raise HTTPError(405)

        org = self._get_org(org_id)
        orgtag = self._get_tag(orgtag_id)
        if orgtag not in org.orgtag_list:
            org.orgtag_list.append(orgtag)
            self.orm_commit()
        return self.redirect_next(org.url)

    @authenticated
    def delete(self, org_id, orgtag_id):
        if not self.moderator:
            raise HTTPError(405)

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
            self.next = org.url
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
                'entity_alias.html',
                obj=obj,
                type_title="Company",
                type_title_plural="Companies",
                type_url="organisation",
                type_alias_list="orgalias_list",
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




