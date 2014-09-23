# -*- coding: utf-8 -*-

from tornado.web import HTTPError

from base import BaseHandler, authenticated
from model_v import get_history



class HistoryHandler(BaseHandler):
    @authenticated
    def get(self):
        if not self.current_user.moderator:
            raise HTTPError(404)
        history = get_history(self.orm, limit=100)
        self.render(
            'history.html',
            history=history,
            )



        


