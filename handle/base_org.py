# -*- coding: utf-8 -*-

from collections import OrderedDict

from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func, literal
from sqlalchemy.sql.expression import case

from tornado.web import HTTPError

from base import BaseHandler

from model import Org, Address, Orgalias, Orgtag, detach


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

    def _create_org(self):
        is_json = self.content_type("application/json")

        name = self.get_argument("name", json=is_json)

        public = self.get_argument_public("public", json=is_json)
        moderation_user = self.current_user

        org = Org(
            name, 
            moderation_user=moderation_user, public=public)

        detach(org)

        return org
    
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



