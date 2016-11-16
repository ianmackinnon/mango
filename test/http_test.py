
import json
import logging
from http.cookies import BaseCookie

import requests
import lxml.html



LOG = logging.getLogger('test_mango_http')



class Http(object):

    @classmethod
    def get_cookies(cls, url):
        response = requests.get(url)
        return response.headers["set-cookie"]

    def __init__(self, host):
        self.host = host

    @staticmethod
    def get_html_title(content):
        page = lxml.html.document_fromstring(content)

        title = page.find(".//title")
        if title is not None:
            return title.text

    def get_http(self, path, headers, host=None):
        if host is None:
            host = self.host

        url = host + path
        response = requests.get(
            url, headers=headers, verify=False, allow_redirects=False)
        if response.status_code == 200:
            title = self.get_html_title(response.text)
        else:
            title = None

        LOG.info("%-64s  %s", url, title or "")
        return response

    def get_json_data(self, path, cookie=None):
        headers = {
            "Accept": "application/json",
        }
        if cookie:
            headers["Cookie"] = cookie

        url = self.host + path
        response = requests.get(
            url, headers=headers, verify=False, allow_redirects=False)

        self.assertEqual(response.status_code, 200, msg=url)
        self.assertNotEqual(response.headers["content-length"], 0)
        self.assertEqual(response.headers["content-type"],
                         'application/json; charset=UTF-8')

        data = json.loads(response.text)

        return data

    @staticmethod
    def get(url):
        response = requests.get(url, verify=False, allow_redirects=False)
        return response

    def get_html(self, path, cookie=None, host=None):
        if host is None:
            host = self.host

        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        url = self.host + path
        response = requests.get(
            url, headers=headers, verify=False, allow_redirects=False)

        # self.assertEqual(response.status_code, 200, msg=host + path)
        self.assertNotEqual(response.headers["content-length"], 0)
        self.assertEqual(response.headers["content-type"],
                         'text/html; charset=UTF-8')

        return response.text

    def get_html_not_found(self, path, cookie=None, host=None):
        if host is None:
            host = self.host

        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response = self.get_http(path, headers, host=host)

        self.assertEqual(response.status_code, 404, msg=host + path)

        return response.text

    def get_html_not_authenticated(self, path, cookie=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response = self.get_http(path, headers)

        self.assertEqual(response.status_code, 302, msg=self.host + path)
        self.assertEqual(response.headers["location"][:11], "/auth/login")

    def get_html_not_authorised(self, path, cookie=None):
        headers = {}
        if cookie:
            headers["Cookie"] = cookie
        response = self.get_http(path, headers)

        self.assertEqual(response.status.code, 403, msg=self.host + path)

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
        # This doesn't work because sessions are now created for guests.

        cookie_text = response.headers.get("set-cookie", None)
        if not cookie_text:
            return False
        cookies = BaseCookie()
        cookies.load(cookie_text)
        morsel = cookies.get(session_cookie_name, None)
        value = morsel and morsel.value

        # Cannot test to see if secure cookie can be parsed as JSON.
        if value:
            try:
                value = json.loads(value)
            except json.decoder.JSONDecodeError:
                print(
                    "Unable to parse value of cookie `%s` as JSON: %s." % (
                        session_cookie_name, repr(value)))

        return bool(value)

    def assert_logged_in(self, response, session_cookie_name):
        self.assertEqual(self.logged_in(response, session_cookie_name), True)

    def assert_not_logged_in(self, response, session_cookie_name):
        pass
        # self.assertEqual(self.logged_in(response, session_cookie_name), False)
