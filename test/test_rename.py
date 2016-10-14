#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=wrong-import-position,import-error
# Allow appending to import path before import
# Must also specify `PYTHONPATH` when invoking Pylint.

import os
import sys
import json
import logging
import unittest
from optparse import OptionParser

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from model import short_name



LOG = logging.getLogger('test_model')



class TestTagShortName(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "dataRename.json")
        with open(path, "r", encoding="utf-8") as json_data:
            cls.known = json.load(json_data)

    def test_html_private(self):
        for name, known_result in self.known:
            result = short_name(name)
            print(name, known_result, result)
            self.assertIsInstance(result, str)
            self.assertEqual(known_result, result)



def main():
    LOG.addHandler(logging.StreamHandler())

    usage = """%prog"""

    parser = OptionParser(usage=usage)
    parser.add_option(
        "-v", "--verbose", dest="verbose",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_option(
        "-q", "--quiet", dest="quiet",
        action="count", default=0,
        help="Suppress warnings.")

    (options, _args) = parser.parse_args()

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + options.verbose - options.quiet))]
    LOG.setLevel(log_level)

    unittest.main()


if __name__ == "__main__":
    main()
