# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import unittest
import httplib2
import lxml.html

log = logging.getLogger('test_mango_http')

class Http(object):

    @classmethod
    def make_http(cls):
        if hasattr(cls, "http"):
            return
        cls.http = httplib2.Http(
            cache=None,
            disable_ssl_certificate_validation=True,
        )
        cls.http.follow_redirects = False

    @classmethod
    def get_cookies(cls, url):
        cls.make_http()
        response, content = cls.http.request(url)
        return response["set-cookie"]
        
    def __init__(self, host):
        self.host = host
        self.make_http()

    def get_html_title(self, content):
        try:
            page = lxml.html.document_fromstring(content)
        except Exception as e:
            print "", e
            return
            
        title = page.find(".//title")
        if title is not None:
            return title.text

    def get_http(self, path, headers, host=None):
        if host == None:
            host = self.host

        url = host + path
        response, content = self.http.request(url, headers=headers)
        if response.status == 200:
            title = self.get_html_title(content)
        else:
            title = None

        log.info(u"%-64s  %s" % (url, title or u""))
        return response, content

    def get_json_data(self, path, cookie=None):
        headers = {
                "Accept": "application/json",
                }
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers)
        
        self.assertEqual(response.status, 200, msg=self.host + path)
        self.assertNotEqual(response["content-length"], 0)
        self.assertEqual(response["content-type"],
                         'application/json; charset=UTF-8')
        
        data = json.loads(content)

        return data

    def get_html(self, path, cookie=None, host=None):
        if host == None:
            host = self.host

        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers, host=host)

#        self.assertEqual(response.status, 200, msg=host + path)
        self.assertNotEqual(response["content-length"], 0)
        self.assertEqual(response["content-type"],
                         'text/html; charset=UTF-8')

        return content
        
    def get_html_not_found(self, path, cookie=None, host=None):
        if host == None:
            host = self.host

        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers, host=host)
        
        self.assertEqual(response.status, 404, msg=host + path)

        return content

    def get_html_not_authenticated(self, path, cookie=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers)
        
        self.assertEqual(response.status, 302, msg=self.host + path)
        self.assertEqual(response["location"][:11], "/auth/login")

    def get_html_not_authorised(self, path, cookie=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response, content = self.get_http(path, headers)
        
        self.assertEqual(response.status, 403, msg=self.host + path)

    def mako_error_test(self, html):
        if "Mako Runtime Error" in html:
            with open(self.error_html, "w") as html_file:
                html_file.write(html)
                html_file.close()
            self.fail("Mako template error. See '%s'." % self.error_html)

    def php_error_test(self, html):
        if ".php</b> on line <b>" in html:
            with open(self.error_html, "w") as html_file:
                html_file.write(html)
                html_file.close()
            self.fail("PHP error. See '%s'." % self.error_html)

    @staticmethod
    def logged_in(response, session_cookie_name):
        if not 'set-cookie' in response:
            return None
        text = response["set-cookie"]
        if not text:
            return None
        cookies = {}
        for cookie in text.split("; "):
            name, value = cookie.split('=', 1)
            cookies[name] = value
        return bool(cookies.get(session_cookie_name, None))

    def assertLoggedIn(self, response, session_cookie_name):
        self.assertEqual(self.logged_in(response, session_cookie_name), True)

    def assertNotLoggedIn(self, response, session_cookie_name):
        self.assertEqual(self.logged_in(response, session_cookie_name), False)
                

