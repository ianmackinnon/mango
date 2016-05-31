#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import unittest
import httplib2
import lxml.html
from optparse import OptionParser

from http_test import Http, log as http_log



log = logging.getLogger('test_mango_web')

host = "https://www.caat.org.uk/resources/mapping"

EVENTS_ENABLED = False
SESSION_COOKIE = "mapping-session"


class HttpTest(unittest.TestCase, Http):
    error_html = "/tmp/mango-error-web.html"

    host = host

    org_id = 416          # BAE Systems
    orgtag_id = 262       # DSEI 2011
    event_id = 85         # Occupy vs arms trade
    eventtag_id = 1       # Activity
    note_org_id = 6136    # BAE
    note_event_id = 2
    note_address_id = 3
    address_id = 1        # Address 1
    contact_id = 189      # BAE

    org_search_name = u"bae"

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

        self.php_path_list_none = [
#            "/resources/countries/%s" % self.country_name_n,
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
            "/organisation/%s" % self.org_n_id,
            "/organisation-tag/%s" % self.orgtag_n_id,
            "/event/%s" % self.event_n_id,
            "/event-tag/%s" % self.eventtag_n_id,
            "/note/%s" % self.note_n_id,
            "/address/%s" % self.address_n_id,
            "/contact/%s" % self.contact_n_id,
        ]

        self.html_path_list_public = [
            "/organisation",
            "/organisation/%s" % self.org_id,
            "/organisation-tag",
            "/organisation-tag/%s" % self.orgtag_id,
            "/event",
            "/event/%s" % self.event_id,
            "/event-tag",
            "/event-tag/%s" % self.eventtag_id,
            "/note",
            "/note/%s" % self.note_org_id,
#            "/note/%s" % self.note_event_id,
#            "/note/%s" % self.note_address_id,
            "/address/%s" % self.address_id,
            "/contact/%s" % self.contact_id,
            "/diary",
        ]

        self.html_path_list_registered = [
            "/organisation/new?view=edit",
            "/event/new?view=edit",
            "/organisation/%s/address" % self.org_id,
            "/event/%s/address" % self.event_id,
            "/organisation/%s/contact" % self.org_id,
            "/event/%s/contact" % self.event_id,
            "/organisation/%s/contact" % self.org_id,
            "/event/%s/contact" % self.org_id,
        ]

        self.html_path_list_moderator = [
            "/organisation-tag/new?view=edit",
            "/event-tag/new?view=edit",
            "/note/new?view=edit",
            "/organisation/%s/tag" % self.org_id,
            "/organisation/%s/note" % self.org_id,
            "/organisation/%s/alias?view=edit" % self.org_id,
            "/organisation-tag/%s/note" % self.orgtag_id,
            "/event/%s/tag" % self.event_id,
            "/event/%s/note" % self.event_id,
            "/event-tag/%s/note" % self.eventtag_id,
            "/moderation/organisation-tag-activity",
            "/moderation/address-not-found",
            "/moderation/organisation-description",
            "/moderation/organisation-inclusion",
            "/moderation/queue",
            "/moderation/organisation-tag-activity",
            "/history",
            "/user",
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
        log.info("Public User / PHP")
        for path in self.php_path_list:
            html = self.get_html(path, host="https://www.caat.org.uk")
            self.php_error_test(html)

    def test_php_none(self):
        log.info("Public User / Non-existant PHP")
        for path in self.php_path_list_none:
            html = self.get_html_not_found(path, host="https://www.caat.org.uk")
            self.php_error_test(html)

    def test_json_public(self):
        log.info("Public User / Authorised JSON")
        for path in self.json_path_list:
            data = self.get_json_data(path)
            self.assertNotEqual(len(data), 0, msg=path)

    def test_html_none(self):
        log.info("Public User / Non-existant HTML")
        for path in self.html_path_list_none:
            self.get_html_not_found(path)

    def test_html_public(self):
        log.info("Public User / Authorised HTML")
        for path in self.html_path_list_public:
            html = self.get_html(path)
            self.mako_error_test(html)

    def test_html_private(self):
        log.info("Public User / Not-authorised HTML")
        for path in self.html_path_list_registered + self.html_path_list_moderator:
            self.get_html_not_found(path)




if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())
    http_log.addHandler(logging.StreamHandler())

    usage = """%prog"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)

    (options, args) = parser.parse_args()
    args = [arg.decode(sys.getfilesystemencoding()) for arg in args]

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + options.verbose - options.quiet))]

    log.setLevel(log_level)
    http_log.setLevel(log_level)

    log.info(u"""

  Testing Mango:

  First run the test server from the application directory to start server with test data. Note: this will delete all data currently in the database.

    make test

  To test any page as a registered user, first visit:

    %s/auth/login/local?user=3

  To test any page as a moderator, first visit:

    %s/auth/login/local?user=1

""" % (host, host))

    unittest.main()
