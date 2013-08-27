#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import sys
import codecs
import getpass
import ConfigParser
from optparse import OptionParser



def get(ini_path, section, key):
    with codecs.open(ini_path, "r", "utf-8") as ini_file:
        config = ConfigParser.ConfigParser()
        config.read(ini_path)

        value = config.get(section, key)
        return value
    


if __name__ == "__main__":
    usage = """%prog INI SECTION KEY

Read INI 
"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)

    (options, args) = parser.parse_args()

    if len(args) != 3:
        parser.print_usage()
        sys.exit(1)

    ini_path, section, key = args
        
    value = get(ini_path, section, key)
    sys.stdout.write(value + u"\n")
