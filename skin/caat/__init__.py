# -*- coding: utf-8 -*-

import re
import urllib

from bs4 import BeautifulSoup
from tornado.template import Loader



re_title = re.compile('(<title>).*?(</title>)', re.IGNORECASE | re.DOTALL)

def caat_fix_links(page):
    soup = BeautifulSoup(page, "lxml")
    
    regex = re.compile("^[/]")
    for link in soup.findAll(href=regex):
        link["href"] = "http://www.caat.org.uk" + link["href"]
    for link in soup.findAll(src=regex):
        link["src"] = "http://www.caat.org.uk" + link["src"]
        
    text = unicode(soup)
    return text
    


def load(**kwargs):
    loader = Loader("skin/caat")
    url_root = kwargs["url_root"]
    static_url = kwargs["static_url"]

    head = loader.load("head.html").generate(
        static_url=static_url,
        stylesheets=kwargs["stylesheets"],
        ).decode("utf-8")

    nav = loader.load("nav.html").generate(
        url_root=url_root,
        ).decode("utf-8")
    
    data = {
        "pagetitle": "Company Map",
        "pagecreated": "2 August 2012",
        "pagedescription": "Expose and challenge the arms trade on your doorstep with CAAT's map of the arms trade.",
        }

    uri = u"http://www.caat.org.uk/resources/app-skin.php"
    uri += "?" + urllib.urlencode(data)

    page = urllib.urlopen(uri).read()

    text = caat_fix_links(page)
    text = text.replace(u"</head>", u"%s</head>" % head)
    text = text.replace(u'<div id="app"', u'%s<div id="app"' % nav)

    splitter = '<!--split-->'
    assert splitter in text
    header_html, footer = text.split(splitter)

    def header(title=None):
        if title is None:
            return header_html
        return re_title.sub(r"\g<1>" + title + r"\g<2>", header_html)

    return {
        "header": header,
        "footer": footer,
        }


def scripts():
    return ["jquery.min.js", "jquery-ui/jquery-ui.min.js"]

def stylesheets():
    return ["jquery-ui/jquery-ui.css"]
