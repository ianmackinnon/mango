#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import unittest
from optparse import OptionParser

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from handle.base import url_rewrite_static



log = logging.getLogger('test_url_rewrite')



class TestClass(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.longMessage = True

        with open(os.path.join(sys.path[0], u"dataUrlRewrite.json")) as fp:
            cls.known_values = json.load(fp)

    def testKnownValues(self):
        for inputs, result_known in self.known_values:
            uri = inputs.pop("uri")
            if "next" in inputs:
                inputs["next_"] = inputs["next"]
                del inputs["next"]
            result_found = url_rewrite_static(uri, **inputs)
            self.assertEqual(result_found, result_known)



if __name__ == "__main__":
    log.addHandler(logging.StreamHandler())

    usage = """%prog"""

    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="Print verbose information for debugging.", default=0)
    parser.add_option("-q", "--quiet", action="count", dest="quiet",
                      help="Suppress warnings.", default=0)

    (options, args) = parser.parse_args()
    args = [arg.decode(sys.getfilesystemencoding()) for arg in args]

    log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG,)[
        max(0, min(3, 1 + options.verbose - options.quiet))]

    log.setLevel(log_level)

    unittest.main()
