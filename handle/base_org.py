# -*- coding: utf-8 -*-

from collections import OrderedDict

from sqlalchemy import and_, or_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func, literal
from sqlalchemy.sql.expression import case

from tornado.web import HTTPError

from base import BaseHandler, MangoBaseEntityHandlerMixin

from model import Org, Address, Orgalias, Orgtag, detach

from model_v import Org_v


max_address_per_page = 26
max_address_pages = 3



class BaseOrgHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    def _get_org(self, id_string,
                 required=True, future_version=False):
        return self._get_entity(Org, "org", "org_id",
                                Org_v, "org_v", "org_v_id",
                                id_string,
                                required, future_version
                                )

    def _create_org(self, id_=None, version=False):
        is_json = self.content_type("application/json")

        name = self.get_argument("name", json=is_json)
        description = self.get_argument("description", None, json=is_json);

        public, moderation_user = self._create_revision()

        if version:
            org = Org_v(
                id_,
                name, description,
                moderation_user=moderation_user, public=public)
        else:
            org = Org(
                name, description,
                moderation_user=moderation_user, public=public)
            
            if id_:
                org.org_id = id_

        detach(org)
        
        return org
    
    def _create_org_v(self, id_):
        return self._create_org(id_, version=True)
    
    def _org_history_query(self, org_id_string):
        return self._history_query(
            Org, "org_id",
            Org_v,
            org_id_string)

    def _get_org_history(self, org_id_string):
        org_v_query, org = self._org_history_query(org_id_string)
        
        org_v_query = org_v_query \
            .order_by(Org_v.a_time.desc())

        return org_v_query.all(), org

    def _count_org_history(self, org_id_string):
        org_v_query, org = self._org_history_query(org_id_string)

        return org_v_query.count() - int(bool(org))

    def _get_name_search_query(self, name=None, name_search=None,
                               visibility=None):
        u"""
        name:         Full name match.
        name_search:  Name contains search, matches from start first.
        visibility:   "public", "pending", "private", "all". Unknown = "public".

        Returns:      A matching list of tuples like (org_id, orgalias_id) where
                      orgalias_id may be None.
        """

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
            name_column = func.lower(name_subquery.c.name)
            name_value = name_search.lower()

            name_query = name_query \
                .filter(name_column.contains(name_value)) \
                .order_by(
                name_column.startswith(name_value).desc(),
                name_column
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
                .filter(Orgtag.base_short.in_(tag_name_list))
            org_alias_query = self.filter_visibility(
                org_alias_query, Orgtag, visibility, secondary=True)

        return org_alias_query



    def _get_org_packet_search(self, name=None, name_search=None,
                               tag_name_list=None,
                               location=None,
                               visibility=None,
                               offset=None,
                               map_view="entity"):

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
                    )) \

        if offset:
            org_alias_address_query = org_alias_address_query \
                .offset(offset)

        org_packet = {
            "location": location and location.to_obj(),
            }

        if (map_view == "marker" or
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
                            public=self.moderator
                            ))

            org_packet["org_list"] = []
            for org_id, data in orgs.items():
                org = data["org"]
                address_obj_list = data["address_obj_list"]
                address_obj_list.sort(
                    key=lambda address_obj: address_obj.get("latitude", None),
                    reverse=True
                    )
                orgtag_obj_list = [orgtag.obj(public=True) for orgtag in org.orgtag_list_public]
                org_packet["org_list"].append(org.obj(
                        public=self.moderator,
                        address_obj_list=address_obj_list,
                        orgtag_obj_list=orgtag_obj_list,
                        ))

        return org_packet



