# -*- coding: utf-8 -*-

from base import BaseHandler



class HomeHandler(BaseHandler):
    def get(self):
        self.redirect(self.url_root + "dsei")
        return
#        self.render('home.html')



        


