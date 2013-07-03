# -*- coding: utf-8 -*-

from tornado.template import Loader


def load(**kwargs):
    loader = Loader("skin/default")

    header = loader.load("header.html").generate(
        static_url=kwargs.get("static_url", None),
        title=kwargs["title"],
        stylesheets=kwargs["stylesheets"],
        )
    footer = loader.load("footer.html").generate()

    return {
        "header": header,
        "footer": footer,
        }
    


def scripts():
    None

def stylesheets():
    None
