#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import unittest
from optparse import OptionParser

sys.path.insert(1, os.path.join(sys.path[0], '..'))

import model

import model_v


log = logging.getLogger('test_model')



class TestClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testOne(self):
        names = [
            u"Org",
            u"Event",
            u"Address",
            u"Note",
            u"Contact",
        ]
        for name in names:
            self.assertEqual(
                getattr(model, name).content,
                getattr(model_v, "%s_v" % name).content,
                )



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
