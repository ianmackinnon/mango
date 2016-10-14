#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
import configparser
from optparse import OptionParser



LOG = logging.getLogger('model')



def get(ini_path, section, key):
    with open(ini_path, "r", encoding="utf-8") as ini_file:
        config = configparser.ConfigParser()
        config.read_file(ini_file)

        value = config.get(section, key)
        return value



def main():
    LOG.addHandler(logging.StreamHandler())

    usage = """%prog INI SECTION KEY

Read INI
"""

    parser = OptionParser(usage=usage)
    parser.add_option(
        "-v", "--verbose", dest="verbose",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_option(
        "-q", "--quiet", dest="quiet",
        action="count", default=0,
        help="Suppress warnings.")

    (options, args) = parser.parse_args()
    args = [arg.decode(sys.getfilesystemencoding()) for arg in args]

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + options.verbose - options.quiet))]
    LOG.setLevel(log_level)

    if len(args) != 3:
        parser.print_usage()
        sys.exit(1)

    ini_path, section, key = args

    value = get(ini_path, section, key)
    sys.stdout.write(value + "\n")



if __name__ == "__main__":
    main()
