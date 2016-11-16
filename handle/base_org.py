
from collections import OrderedDict

from sqlalchemy import and_, exists
from sqlalchemy.sql import func, literal
from sqlalchemy.sql.expression import case

from model import User, Org, Address, Orgalias, Orgtag, detach, org_orgtag

from model_v import Org_v, \
    accept_org_address_v

from handle.base import BaseHandler, MangoBaseEntityHandlerMixin

MAX_ORG_PER_PAGE = 20
MAX_ADDRESS_PER_PAGE = 26
MAX_ADDRESS_PAGES = 3



class BaseOrgHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    def _get_org(self, org_id, required=True):
        return self._get_entity(
            Org,
            "org_id",
            "org",
            org_id,
            required,
        )

    def _get_org_v(self, org_v_id):
        return self._get_entity_v(
            Org,
            "org_id",
            Org_v,
            "org_v_id",
            "org",
            org_v_id,
        )

    def _touch_org(self, org_id):
        return self._touch_entity(
            Org,
            "org_id",
            "org",
            self._decline_org_v,
            org_id,
        )

    def _create_org(self, id_=None, version=False):
        # pylint: disable=redefined-variable-type
        # Entity may be a previous version ("_v")

        is_json = self.content_type("application/json")

        name = self.get_argument("name", is_json=is_json)
        description = self.get_argument("description", None, is_json=is_json)
        end_date = self.get_argument_date("end_date", None, is_json=is_json)

        public, moderation_user = self._create_revision()

        if version:
            org = Org_v(
                id_,
                name, description, end_date,
                moderation_user=moderation_user, public=public)
        else:
            org = Org(
                name, description, end_date,
                moderation_user=moderation_user, public=public)

            if id_:
                org.org_id = id_

        detach(org)

        return org

    def _create_org_v(self, org_id):
        return self._create_org(org_id, version=True)

    @staticmethod
    def _decline_org_v(org_id, moderation_user):
        org = Org_v(
            org_id,
            "DECLINED",
            moderation_user=moderation_user, public=None)
        org.existence = False

        detach(org)

        return org

    def _org_history_query(self, org_id):
        return self._history_query(
            Org, "org_id",
            Org_v,
            org_id)

    def _get_org_history(self, org_id):
        org_v_query, org = self._org_history_query(org_id)

        org_v_query = org_v_query \
            .order_by(Org_v.org_v_id.desc())

        return org_v_query.all(), org

    def _count_org_history(self, org_id):
        org_v_query, _org = self._org_history_query(org_id)

        return org_v_query.count()

    def _get_org_latest_a_time(self, org_id):
        # pylint: disable=singleton-comparison
        # Cannot use `is` in SQLAlchemy filters

        org_v = self.orm.query(Org_v.a_time) \
            .join((User, Org_v.moderation_user)) \
            .filter(Org_v.org_id == org_id) \
            .filter(User.moderator == True) \
            .order_by(Org_v.org_v_id.desc()) \
            .first()

        return org_v and org_v.a_time or None

    def _after_org_accept_new(self, org):
        accept_org_address_v(self.orm, org.org_id)

    def _get_name_search_query(self, name=None, name_search=None,
                               visibility=None):
        """
        name:         Full name match.
        name_search:  Name contains search, matches from start first.
        visibility:   "public", "pending", "private", "all". Unknown = "public".

        Returns:      A matching list of tuples like (org_id, orgalias_id) where
                      orgalias_id may be None.
        """
        # pylint: disable=no-member
        # (`Orgalias.org` is generated)

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
                )],
                else_=func.min(name_subquery.c.orgalias_id),
            ).label("orgalias_id")
        )

        if name:
            name_query = name_query \
                .filter(name_subquery.c.name == name)
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
            self,
            name=None,
            name_search=None,
            tag_name_list=None,
            tag_all=False,
            visibility=None
    ):

        name_query = self._get_name_search_query(name, name_search, visibility)
        name_subquery = name_query.subquery()

        org_alias_query = self.orm.query(Org, Orgalias) \
            .join(name_subquery, Org.org_id == name_subquery.c.org_id) \
            .outerjoin(Orgalias,
                       Orgalias.orgalias_id == name_subquery.c.orgalias_id)

        if tag_name_list:
            if tag_all:
                for tag_name in tag_name_list:
                    e1 = self.orm.query(org_orgtag) \
                        .filter(org_orgtag.c.org_id == Org.org_id) \
                        .join(Orgtag) \
                        .filter(Orgtag.base_short == tag_name)
                    org_alias_query = org_alias_query \
                        .filter(exists(e1.statement))
            else:
                org_alias_query = org_alias_query \
                    .join((Orgtag, Org.orgtag_list)) \
                    .filter(Orgtag.base_short.in_(tag_name_list))


        return org_alias_query



    def _get_org_packet_search(self, name=None, name_search=None,
                               tag_name_list=None,
                               tag_all=False,
                               location=None,
                               visibility=None,
                               offset=None,
                               page_view="entity"):

        org_alias_query = self._get_org_alias_search_query(
            name=name,
            name_search=name_search,
            tag_name_list=tag_name_list,
            tag_all=tag_all,
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

        org_packet = {
            "location": location and location.to_obj(),
            }

        if page_view == "marker":
            # Just want markers for all matches.
            org_packet["markerList"] = []
            for org, alias, address in org_alias_address_query:
                org_packet["markerList"].append({
                    "name": org.name,
                    "alias": alias and alias.name,
                    "url": org.url,
                    "latitude": address and address.latitude,
                    "longitude": address and address.longitude,
                })
        elif page_view == "map":
            if (
                    org_alias_address_query.count() >
                    MAX_ADDRESS_PER_PAGE * MAX_ADDRESS_PAGES
            ):
                # More than 3 pages of addresses for the map. Want markers
                # for all matches, and names of the first 10 matching
                # companies (with offset).

                orgs = OrderedDict()
                org_packet["markerList"] = []
                for org, alias, address in org_alias_address_query:
                    if address and address.latitude:
                        org_packet["markerList"].append({
                            "name": org.name,
                            "url": org.url,
                            "latitude": address.latitude,
                            "longitude": address.longitude,
                        })
                    if org.org_id not in orgs:
                        orgs[org.org_id] = {
                            "org": org,
                            "alias": alias and alias.name,
                            }
                org_packet["orgLength"] = len(orgs)
                org_packet["orgList"] = []
                for data in list(orgs.values())[
                        (offset or 0):(offset or 0) + MAX_ORG_PER_PAGE]:
                    org = data["org"]
                    org_packet["orgList"].append(org.obj(
                        alias=data["alias"],
                        public=self.moderator,
                        description=False,
                    ))
            else:
                # Get all addresses, don't send markers.
                orgs = OrderedDict()
                for org, alias, address in org_alias_address_query:
                    if org.org_id not in orgs:
                        orgs[org.org_id] = {
                            "org": org,
                            "alias": alias and alias.name,
                            "addressList": [],
                            }
                    if address:
                        orgs[org.org_id]["addressList"].append(address.obj(
                            public=self.moderator
                        ))

                org_packet["orgLength"] = len(orgs)
                org_packet["orgList"] = []
                for data in list(orgs.values()):
                    org = data["org"]
                    address_list = data["addressList"]
                    address_list.sort(
                        key=lambda address_obj: address_obj.get(
                            "latitude", None),
                        reverse=True
                        )
                    org_packet["orgList"].append(org.obj(
                        alias=data["alias"],
                        public=self.moderator,
                        description=False,
                        address_list=address_list,
                    ))
        else:
            # Get all orgs, no addresses
            orgs = OrderedDict()
            for org, alias, address in org_alias_address_query:
                if org.org_id not in orgs:
                    orgs[org.org_id] = {
                        "org": org,
                        "alias": alias and alias.name,
                        }

            org_packet["orgList"] = []
            for data in list(orgs.values()):
                org = data["org"]
                org_packet["orgList"].append(org.obj(
                    alias=data["alias"],
                    public=self.moderator,
                    description=False,
                ))

        return org_packet
