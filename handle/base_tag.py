# -*- coding: utf-8 -*-

from sqlalchemy.sql import func
from sqlalchemy.orm.exc import NoResultFound

from tornado.web import HTTPError

from base import BaseHandler, MangoBaseEntityHandlerMixin
from model import short_name, detach, url_directory



class BaseTagHandler(BaseHandler, MangoBaseEntityHandlerMixin):
    Tag = None
    Entity = None
    tag_id = None
    entity_id = None
    cross_table = None
    tag_type = None

    def _get_tag(self, tag_id, options=None):
        query = self.orm.query(self.Tag)\
            .filter(getattr(self.Tag, self.tag_id)==tag_id)

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
        name, description, public = self._get_arguments()

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

        

    def _get_arguments(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)
        description = self.get_argument("description", None, json=is_json)
        path = self.get_argument("path", None, json=is_json)
        public = self.get_argument_public("public", json=is_json)
        
        if name and path:
            name = u"%s | %s" % (path.strip(), name.strip())
            
        return name, description, public

    def _get_path_list(self):
        path_list = self.orm.query(self.Tag.path.distinct().label("path")) \
            .filter(self.Tag.path != None) \
            .group_by(self.Tag.path) \
            .order_by(func.count(getattr(self.Tag, self.tag_id)).desc()) \
            .all()
        
        return [entry.path for entry in path_list]
        
    def _get_tag_entity_count_search(self, name=None, name_short=None, base=None, base_short=None, path=None, search=None, sort=None, visibility=None):

        tag_list = self.orm.query(self.Tag)
        entity_q = self.orm.query(self.Entity)

        tag_list = self.filter_visibility(tag_list, self.Tag, visibility)
        entity_q = self.filter_visibility(entity_q, self.Entity, visibility).subquery()

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
            .outerjoin((s, getattr(self.Tag, self.tag_id) == getattr(s.c, self.tag_id)))

        if search:
            results = results\
                .order_by(search_member.startswith(search).desc())

        if sort:
            sort_dict = {
                "name": getattr(self.Tag, "name_short" if path else "base_short"),
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
        name = self.get_argument("name", None, json=is_json)
        name_short = self.get_argument("name_short", None, json=is_json)
        base = self.get_argument("short", None, json=is_json)
        base_short = self.get_argument("base_short", None, json=is_json)
        path = self.get_argument_bool("path", None, json=is_json)
        search = self.get_argument("search", None, json=is_json)
        sort = self.get_argument("sort", None, json=is_json)

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

        entity_url = url_directory[self.entity_type]

        tag_list = []
        for tag, entity_count in entity_count_list:
            tag_list.append(tag.obj(**{
                "public": self.moderator,
                "tagged_count": entity_count,
                "tagged_url": entity_url,
            }))

        return (tag_list, name, name_short, base, base_short,
                path, search, sort)

