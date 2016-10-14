# -*- coding: utf-8 -*-

from sqlalchemy.sql import func
from sqlalchemy.orm.exc import NoResultFound

from tornado.web import HTTPError

from model import short_name, detach, URL_DIRECTORY

from handle.base import BaseHandler, MangoBaseEntityHandlerMixin



class BaseTagHandler(BaseHandler, MangoBaseEntityHandlerMixin):

    # Override:
    tag_id = None
    entity_id = None
    entity_type = None
    cross_table = None
    tag_type = None

    # Override:
    def Tag(self, *args, **kwargs):
        # pylint: disable=invalid-name
        # Allow `Tag` as abstract class names
        raise NotImplementedError

    # Override:
    def Entity(self, *args, **kwargs):
        # pylint: disable=invalid-name
        # Allow `Entity` as abstract class names
        raise NotImplementedError

    def _get_tag(self, tag_id, options=None):
        query = self.orm.query(self.Tag)\
            .filter(getattr(self.Tag, self.tag_id) == tag_id)

        if not self.moderator:
            query = query \
                .filter_by(public=True)

        if options:
            query = query \
                .options(*options)

        try:
            tag = query.one()
        except NoResultFound:
            raise HTTPError(404, "%d: No such orgtag" % tag_id)

        return tag

    def _create_tag(self, id_=None):
        name, description, public = self._get_entity_arguments()

        moderation_user = self.current_user

        tag = self.Tag(
            name,
            description=description,
            moderation_user=moderation_user,
            public=public,
            )

        if id_:
            setattr(tag, self.tag_id, id_)

        detach(tag)

        return tag

    def _get_entity_arguments(self):
        # pylint: disable=maybe-no-member
        # (`self.get_argument` appears to return list)

        is_json = self.content_type("application/json")
        name = self.get_argument("name", is_json=is_json)
        description = self.get_argument("description", None, is_json=is_json)
        path = self.get_argument("path", None, is_json=is_json)
        public = self.get_argument_public("public", is_json=is_json)

        if name and path:
            name = "%s | %s" % (path.strip(), name.strip())

        return name, description, public

    def _get_path_list(self):
        path_list = self.orm.query(self.Tag.path.distinct().label("path")) \
            .filter(self.Tag.path != None) \
            .group_by(self.Tag.path) \
            .order_by(func.count(getattr(self.Tag, self.tag_id)).desc()) \
            .all()

        return [entry.path for entry in path_list]

    def _get_tag_entity_count_search(
            self,
            name=None, name_short=None, base=None, base_short=None,
            path=None, search=None, sort=None, visibility=None):

        tag_list = self.orm.query(self.Tag)
        entity_q = self.orm.query(self.Entity)

        tag_list = self.filter_visibility(tag_list, self.Tag, visibility)
        entity_q = self.filter_visibility(
            entity_q, self.Entity, visibility).subquery()

        if name:
            tag_list = tag_list.filter_by(name=name)

        if name_short:
            tag_list = tag_list.filter_by(name_short=name_short)

        if base:
            tag_list = tag_list.filter_by(base=base)

        if base_short:
            tag_list = tag_list.filter_by(base_short=base_short)

        if search:
            search = search.lower()
            if path:
                search = short_name(search, allow_end_pipe=True)
                search_member = func.lower(self.Tag.name_short)
            else:
                search = search.rsplit("|")[-1].strip()
                if search:
                    search = short_name(search)
                    search_member = func.lower(self.Tag.base_short)
            tag_list = tag_list \
                .filter(search_member.contains(search))

        cross_tag_id = getattr(self.cross_table.c, self.tag_id)
        cross_entity_id = getattr(self.cross_table.c, self.entity_id)
        entity_id = getattr(entity_q.c, self.entity_id)

        s = self.orm.query(
            cross_tag_id,
            func.count(cross_entity_id).label("count")
            )\
            .join((entity_q, entity_id == cross_entity_id))\
            .group_by(cross_tag_id)\
            .subquery()

        results = tag_list\
            .add_columns(s.c.count)\
            .outerjoin((s, getattr(self.Tag, self.tag_id) ==
                        getattr(s.c, self.tag_id)))

        if search:
            results = results\
                .order_by(search_member.startswith(search).desc())

        if sort:
            sort_dict = {
                "name": getattr(self.Tag,
                                "name_short" if path else "base_short"),
                "date": getattr(self.Tag, "a_time").desc(),
                "freq": s.c.count.desc(),
                }

            results = results\
                .order_by(sort_dict[sort])

        tag_and_org_count_list = results.all()

        return tag_and_org_count_list

    def get_argument_sort(self, json=False):
        return self.get_argument_allowed(
            "sort", ("name", "date", "freq"), None, json)

    def _get_tag_search_args(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", None, is_json=is_json)
        name_short = self.get_argument("name_short", None, is_json=is_json)
        base = self.get_argument("short", None, is_json=is_json)
        base_short = self.get_argument("base_short", None, is_json=is_json)
        path = self.get_argument_bool("path", None, is_json=is_json)
        search = self.get_argument("search", None, is_json=is_json)
        sort = self.get_argument("sort", None, is_json=is_json)

        entity_count_list = self._get_tag_entity_count_search(
            name=name,
            name_short=name_short,
            base=base,
            base_short=base_short,
            path=path,
            search=search,
            sort=sort,
            visibility=self.parameters.get("visibility", None),
            )

        entity_url = URL_DIRECTORY[self.entity_type]

        tag_list = []
        for tag, entity_count in entity_count_list:
            tag_list.append(tag.obj(**{
                "public": self.moderator,
                "tagged_count": entity_count,
                "tagged_url": entity_url,
            }))

        return (tag_list, name, name_short, base, base_short,
                path, search, sort)
