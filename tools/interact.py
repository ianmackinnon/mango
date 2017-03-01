#!/usr/bin/env python3

# pylint: disable=wrong-import-position
# Adding working directory to system path

# pylint: disable=unused-import, unused-variable
# Variables for use in interactive session

import os
import sys
import code
import atexit
import logging
import argparse
import readline

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(".")

from mysql import mysql
from model import CONF_PATH, engine_disable_mode, attach_search
from model import User, Org, Orgalias, Note, Address, Orgtag, Contact, Medium



LOG = logging.getLogger("interact")



# https://docs.python.org/3.5/library/readline.html
class HistoryConsole(code.InteractiveConsole):
    def __init__(self, locals_=None, filename="<console>",
                 histfile=os.path.expanduser("~/.console-history")):
        code.InteractiveConsole.__init__(self, locals_, filename)
        self.init_history(histfile)

    def init_history(self, histfile):
        readline.parse_and_bind("tab: complete")
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
            except FileNotFoundError:
                pass
            atexit.register(self.save_history, histfile)

    @staticmethod
    def save_history(histfile):
        readline.set_history_length(1000)
        readline.write_history_file(histfile)



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Interactive Python session with database access.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    parser.add_argument(
        "-s", "--search",
        action="store_true",
        help="Include access to Elasticsearch.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)

    connection_url = mysql.connection_url_admin(CONF_PATH)
    engine = create_engine(connection_url)
    # engine_disable_mode(engine, "ONLY_FULL_GROUP_BY")
    session_ = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    orm = session_()

    if args.search:
        attach_search(engine, orm)
        es = orm.get_bind().search

    variables = globals().copy()
    variables.update(locals())
    shell = HistoryConsole(variables)
    shell.interact()



if __name__ == "__main__":
    main()
