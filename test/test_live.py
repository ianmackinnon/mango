#!/usr/bin/env python3

import logging
import argparse
import unittest


from http_test import Http, LOG as HTTP_LOG



LOG = logging.getLogger('test_mango_web')

HOST = "https://www.caat.org.uk/resources/mapping"

EVENTS_ENABLED = False
SESSION_COOKIE = "mapping-session"


class HttpTest(unittest.TestCase, Http):
    error_html = "/tmp/mango-error-web.html"

    host = HOST

    org_id = 416          # BAE Systems
    orgtag_id = 262       # DSEI 2011
    event_id = 85         # Occupy vs arms trade
    eventtag_id = 1       # Activity
    note_org_id = 6136    # BAE
    note_event_id = 2
    note_address_id = 3
    address_id = 1        # Address 1
    contact_id = 189      # BAE

    org_search_name = "bae"

    org_n_id = 4040404
    orgtag_n_id = 4040404
    event_n_id = 4040404
    eventtag_n_id = 4040404
    note_n_id = 4040404
    address_n_id = 4040404
    contact_n_id = 4040404

    country_name = "egypt"
    country_name_n = "eg"

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        Http.__init__(self, self.host)

        self.php_path_list = [
            "/resources/countries/%s" % self.country_name,
        ]

        self.json_path_list = [
            "/organisation",
            "/organisation-tag",
            "/event",
            "/event-tag",
            "/organisation/search?name=%s" % self.org_search_name,
            "/organisation?json=true",
            "/event?json=true",
            "/event?json=true&past=true",
            "/event?json=true&pageView=map",
            "/event?json=true&pageView=map&past=true",
            "/dsei-target",
        ]

        self.html_path_list_none = [
        ]

        self.html_path_list_public = [
            # "/note/%s" % self.note_event_id,
            # "/note/%s" % self.note_address_id,
        ]

        self.html_path_list_registered = [
        ]

        self.html_path_list_moderator = [
        ]

        def removed(list_, matches):
            out = []
            for i in range(len(list_) - 1, 0, -1):
                url = list_[i]
                for match in matches:
                    if match in url:
                        out.append(list_.pop(i))
            return out

        matches = ["/event", "/diary"]
        if not EVENTS_ENABLED:
            removed(self.json_path_list, matches)
            self.html_path_list_none += \
                removed(self.html_path_list_public, matches)
            self.html_path_list_none += \
                removed(self.html_path_list_registered, matches)
            self.html_path_list_none += \
                removed(self.html_path_list_moderator, matches)



# Duplicated in test_web
class TestPublic(HttpTest):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True

    def test_php_public(self):
        LOG.info("Public User / PHP")
        for path in self.php_path_list:
            html = self.get_html(path, host="https://www.caat.org.uk")
            self.php_error_test(html)

    def test_json_public(self):
        LOG.info("Public User / Authorised JSON")
        for path in self.json_path_list:
            data = self.get_json_data(path)
            self.assertNotEqual(len(data), 0, msg=path)

    def test_html_none(self):
        LOG.info("Public User / Non-existant HTML")
        for path in self.html_path_list_none:
            self.get_html_not_found(path)

    def test_html_public(self):
        LOG.info("Public User / Authorised HTML")
        for path in self.html_path_list_public:
            html = self.get_html(path)
            self.mako_error_test(html)

    def test_html_private(self):
        LOG.info("Public User / Not-authorised HTML")
        for path in (
                self.html_path_list_registered +
                self.html_path_list_moderator
        ):
            self.get_html_not_found(path)



def main():
    LOG.addHandler(logging.StreamHandler())
    HTTP_LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Test live instances of web application.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)
    HTTP_LOG.setLevel(level)

    LOG.info("""

  Testing Mango:

  First run the test server from the application directory to start server with test data. Note: this will delete all data currently in the database.

    make test

  To test any page as a registered user, first visit:

    %s/auth/login/local?user=3

  To test any page as a moderator, first visit:

    %s/auth/login/local?user=1

""", HOST, HOST)

    unittest.main()



if __name__ == "__main__":
    main()
