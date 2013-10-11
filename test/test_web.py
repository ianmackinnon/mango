#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import unittest
import httplib2
import lxml.html



host = "http://localhost:8802"

org_id = 1
orgtag_id = 1
event_id = 1
eventtag_id = 1
note_id = 1
address_id = 1
contact_id = 1



class Http(object):

    json_path_list = [
        "/organisation",
        "/organisation-tag",
        "/event",
        "/event-tag",
        ]

    html_path_list_public = [
        "/organisation",
        "/organisation/%s" % org_id,
        "/organisation-tag",
        "/organisation-tag/%s" % orgtag_id,
        "/event",
        "/event/%s" % event_id,
        "/event-tag",
        "/event-tag/%s" % eventtag_id,
        "/note",
        "/note/%s" % note_id,
        "/address/%s" % address_id,
        "/contact/%s" % contact_id,
        ]

    html_path_list_registered = [
        "/organisation/new",
        "/event/new",
        "/organisation/%s/address" % org_id,
        "/event/%s/address" % event_id,
        "/organisation/%s/contact" % org_id,
        "/event/%s/contact" % event_id,
        ]

    html_path_list_moderator = [
        "/organisation-tag/new",
        "/event-tag/new",
        "/note/new",
        "/organisation/%s/tag" % org_id,
        "/organisation/%s/note" % org_id,
        "/organisation/%s/alias?view=edit" % org_id,
        "/organisation-tag/%s/note" % orgtag_id,
        "/event/%s/tag" % event_id,
        "/event/%s/note" % event_id,
        "/event-tag/%s/note" % eventtag_id,
        ]

    def get_html_title(self, content):
        try:
            page = lxml.html.document_fromstring(content)
        except Exception as e:
            print "", e
            return
            
        title = page.find(".//title")
        if title is not None:
            return title.text

    def get_http(self, path, headers):
        url = host + path
        response, content = self.http.request(url, headers=headers)
        if response.status == 200:
            title = self.get_html_title(content)
        else:
            title = None

        print u"%-64s  %s" % (url, title or u"")
        return response, content

    def get_json_data(self, path, cookie=None):
        headers = {
                "Accept": "application/json",
                }
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers)
        
        self.assertEqual(response.status, 200, msg=path)
        self.assertNotEqual(response["content-length"], 0)
        self.assertEqual(response["content-type"],
                         'application/json; charset=UTF-8')
        
        data = json.loads(content)

        return data

    def get_html(self, path, cookie=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers)
        
        self.assertEqual(response.status, 200, msg=path)
        self.assertNotEqual(response["content-length"], 0)
        self.assertEqual(response["content-type"],
                         'text/html; charset=UTF-8')

        return content
        
    def get_html_not_authenticated(self, path, cookie=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers)
        
        self.assertEqual(response.status, 302, msg=path)
        self.assertEqual(response["location"][:11], "/auth/login")

    def get_html_not_authorised(self, path, cookie=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers)
        
        self.assertEqual(response.status, 403, msg=path)



class TestPublic(unittest.TestCase, Http):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.http = httplib2.Http(cache=None)
        cls.http.follow_redirects = False
        
    def test_json_public(self):
        print
        for path in self.json_path_list:
            data = self.get_json_data(path)
            self.assertNotEqual(len(data), 0, msg=path)

    def test_html_public(self):
        print
        for path in self.html_path_list_public:
            html = self.get_html(path)
            self.assertNotIn("Mako Runtime Error", html, msg=path)

    def test_html_private(self):
        print
        for path in self.html_path_list_registered + self.html_path_list_moderator:
            self.get_html_not_authenticated(path)



class TestRegistered(unittest.TestCase, Http):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.http = httplib2.Http(cache=None)
        cls.http.follow_redirects = False
        url = host + "/auth/login/local?user=3"
        response, content = cls.http.request(url)
        cls.cookie = response["set-cookie"]
        
    def test_json_public(self):
        print
        for path in self.json_path_list:
            data = self.get_json_data(path, cookie=self.cookie)
            self.assertNotEqual(len(data), 0, msg=path)

    def test_html_public(self):
        print
        for path in self.html_path_list_public + self.html_path_list_registered:
            html = self.get_html(path, cookie=self.cookie)
            self.assertNotIn("Mako Runtime Error", html, msg=path)

    def test_html_private(self):
        print
        for path in self.html_path_list_moderator:
            self.get_html_not_authorised(path, cookie=self.cookie)



class TestModerator(unittest.TestCase, Http):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True
        cls.http = httplib2.Http(cache=None)
        cls.http.follow_redirects = False
        url = host + "/auth/login/local?user=1"
        response, content = cls.http.request(url)
        cls.cookie = response["set-cookie"]
        
    def test_json_public(self):
        print
        for path in self.json_path_list:
            data = self.get_json_data(path, cookie=self.cookie)
            self.assertNotEqual(len(data), 0, msg=path)

    def test_html_public(self):
        print
        for path in self.html_path_list_public + self.html_path_list_registered + self.html_path_list_registered:
            html = self.get_html(path, cookie=self.cookie)
            self.assertNotIn("Mako Runtime Error", html, msg=path)






            
if __name__ == "__main__":
    unittest.main()
                
