# -*- coding: utf-8 -*-

from tornado.template import Loader


def load(**kwargs):
    loader = Loader("skin/default")

    def header(title=None):
        return loader.load("header.html").generate(
            static_url=kwargs.get("static_url", None),
            title=title or "",
            stylesheets=kwargs["stylesheets"],
            ).decode("utf-8")
    footer = loader.load("footer.html").generate().decode("utf-8")

    return {
        "header": header,
        "footer": footer,
    }



def scripts():
    "Scripts that will be provided by the host site"
    return None

def stylesheets():
    "Stylesheets that will be provided by the host site"
    return None
