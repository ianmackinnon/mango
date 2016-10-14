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

from handle.base import url_rewrite_static



LOG = logging.getLogger('test_url_rewrite')



class TestClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True

        data_path = os.path.join(sys.path[0], "dataUrlRewrite.json")

        with open(data_path) as fp:
            cls.known_values = json.load(fp)

    def test_known_values(self):
        for inputs, result_known in self.known_values:
            uri = inputs.pop("uri")
            if "next" in inputs:
                inputs["next_"] = inputs["next"]
                del inputs["next"]
            result_found = url_rewrite_static(uri, **inputs)
            self.assertEqual(result_found, result_known)



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
