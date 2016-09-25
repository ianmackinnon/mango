# -*- coding: utf-8 -*-

from tornado.web import HTTPError

from model_v import get_history

from handle.base import BaseHandler, authenticated



class HistoryHandler(BaseHandler):
    @authenticated
    def get(self):
        if not self.current_user.moderator:
            raise HTTPError(404)

        is_json = self.content_type("application/json")
        offset = self.get_argument_int("offset", None, is_json=is_json)

        history = get_history(self.orm, offset=offset, limit=50)

        self.render(
            'history.html',
            history=history,
        )
