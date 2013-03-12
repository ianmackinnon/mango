# -*- coding: utf-8 -*-

from sqlalchemy.sql import func

from base import BaseHandler



class BaseTagHandler(BaseHandler):
    Tag = None
    tag_id = None

    def _get_arguments(self):
        is_json = self.content_type("application/json")
        name = self.get_argument("name", json=is_json)
        path = self.get_argument("path", None, json=is_json)
        public = self.get_argument_public("public", json=is_json)
        
        if name and path:
            name = u"%s | %s" % (path.strip(), name.strip())
            
        return name, public

    def _get_path_list(self):
        path_list = self.orm.query(self.Tag.path.distinct().label("path")) \
            .filter(self.Tag.path != None) \
            .group_by(self.Tag.path) \
            .order_by(func.count(getattr(self.Tag, self.tag_id)).desc()) \
            .all()
        
        return [entry.path for entry in path_list]
        

