# -*- coding: utf-8 -*-

from base import BaseHandler



class HomeHandler(BaseHandler):
    def get(self):
        self.render('home.html')



        


