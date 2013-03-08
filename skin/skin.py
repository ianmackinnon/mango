#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import urllib

from BeautifulSoup import BeautifulSoup



def variable(name=None):
    if name in ["header1", "header2", "footer"]:
        return caat_base_header_footer()
    if name in ["diary_header", "diary_footer"]:
        return caat_diary_header_footer()
    return {}



def caat_fix_links(page):
    soup = BeautifulSoup(page)
    
    regex = re.compile("^[/]")
    for link in soup.findAll(href=regex):
        link["href"] = "http://www.caat.org.uk" + link["href"]
    for link in soup.findAll(src=regex):
        link["src"] = "http://www.caat.org.uk" + link["src"]
        
    text = unicode(soup)
    return text
    


ROOT_URL = u"http://www.caat.org.uk/resources/mapping"


def caat_base_header_footer():
    uri = "%s/%s" % (ROOT_URL, "caat-mapping.php")

    page = urllib.urlopen(uri).read()

    text = caat_fix_links(page)

    text = text.replace("<head>",
                        """
<head>
  <!--[if lt IE 9]>
  <script src="//html5shiv.googlecode.com/svn/trunk/html5.js"></script>
  <![endif]-->

""")

    splitter_1 = '</head>'
    splitter_2 = '<div id="mapping">'

    assert splitter_2 in text

    header, footer = text.split(splitter_2)
    header += splitter_2

    assert splitter_1 in header

    header1, header2 = header.split(splitter_1)
    header2 = splitter_1 + header2

    del header
    
    return {
        "header1": header1,
        "header2": header2,
        "footer": footer,
        }



def caat_diary_header_footer():
    uri = "%s/%s" % (ROOT_URL, "caat-diary.php")

    page = urllib.urlopen(uri).read()

    text = caat_fix_links(page)

    splitter = '<div id="diary"></div>\n'

    assert splitter in text

    header, footer = text.split(splitter)
    
    return {
        "diary_header": header,
        "diary_footer": footer,
        }
