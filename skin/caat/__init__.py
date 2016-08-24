# -*- coding: utf-8 -*-

import re
import os
import json
import urllib
import urllib2

from bs4 import BeautifulSoup
from tornado.template import Loader



DEFAULT_PROTOCOL = u"http"
DEFAULT_HOST = u"www.caat.org.uk"
DEFAULT_DOMAIN = u"caat.org.uk"
MAX_TITLE_LENGTH = 5

re_title = re.compile('(<title>).*?(</title>)', re.IGNORECASE | re.DOTALL)



with open(os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "page.json")) as handle:
    PAGE_DATA = json.load(handle)



def caat_fix_links(page, protocol=DEFAULT_PROTOCOL, host=DEFAULT_HOST):
    soup = BeautifulSoup(page, "lxml")

    regex = re.compile("^[/]")
    for link in soup.findAll(href=regex):
        link["href"] = "%s://%s%s" % (protocol, host, link["href"])
    for link in soup.findAll(src=regex):
        link["src"] = "%s://%s%s" % (protocol, host, link["src"])

    text = unicode(soup)
    return text



def load(**kwargs):
    loader = Loader("skin/caat")

    url_root = kwargs["url_root"]
    static_url = kwargs["static_url"]
    protocol = kwargs.get("protocol", DEFAULT_PROTOCOL)
    host = kwargs.get("host", DEFAULT_HOST)
    offsite = kwargs.get("offsite", None)
    title_list = kwargs.get("title_list", None) or []
    stylesheets = kwargs.get("stylesheets", None)
    header_function = kwargs.get("header_function", None)
    load_nav = kwargs.get("load_nav", None)

    if not (host and DEFAULT_DOMAIN in host):
        host = DEFAULT_HOST

    head = loader.load("head.html").generate(
        static_url=static_url,
        stylesheets=stylesheets,
        ).decode("utf-8")

    if load_nav:
        nav = loader.load("nav.html").generate(
            url_root=url_root,
            ).decode("utf-8")

    uri = u"%s://%s/resources/app-skin" % (protocol, host)
    uri += "?" + urllib.urlencode(PAGE_DATA)

    page = urllib2.urlopen(uri).read()

    text = page
    if offsite:
        text = caat_fix_links(page, protocol=protocol, host=host)
    text = text.replace("</head>", "%s</head>" % head)
    if load_nav:
        text = text.replace(u'<div id="app"', u'%s<div id="app"' % nav)

    splitter = '<!--split-->'
    assert splitter in text
    header_html, footer = text.split(splitter)

    def header(title=None):
        if title is None:
            return header_html
        return re_title.sub(r"\g<1>" + title + r"\g<2>", header_html)

    components = {
        "header": header,
        "footer": footer,
        }

    title_base = [u"CAAT", PAGE_DATA["pagetitle"]]
    if header_function:
        # Give the templates a function to set the title
        components["title_base"] = title_base
        components["title_list"] = title_list
    else:
        # Set the title now
        title = " - ".join((title_base + title_list)[:MAX_TITLE_LENGTH])
        components["header"] = header(title)

    return components


def scripts():
    return PAGE_DATA.get("scripts", None)

def stylesheets():
    return PAGE_DATA.get("stylesheets", None)
