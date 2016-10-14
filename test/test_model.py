#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import unittest
from optparse import OptionParser

import model
import model_v



LOG = logging.getLogger('test_model')



class TestModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.longMessage = True

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_one(self):
        names = [
            "Org",
            "Event",
            "Address",
            "Note",
            "Contact",
        ]
        for name in names:
            self.assertEqual(
                getattr(model, name).content,
                getattr(model_v, "%s_v" % name).content,
                )



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
