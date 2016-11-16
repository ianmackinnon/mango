#!/usr/bin/env python3

# pylint: disable=wrong-import-position,import-error
# Allow appending to import path before import
# Must also specify `PYTHONPATH` when invoking Pylint.

import os
import sys
import logging
import argparse
import unittest

sys.path.insert(1, os.path.join(sys.path[0], '..'))

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

    parser = argparse.ArgumentParser(
        description="Unittest ORM models.")
    parser.add_argument(
        "--verbose", "-v",
        action="count", default=0,
        help="Print verbose information for debugging.")
    parser.add_argument(
        "--quiet", "-q",
        action="count", default=0,
        help="Suppress warnings.")

    args = parser.parse_args()

    level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[
        max(0, min(3, 1 + args.verbose - args.quiet))]
    LOG.setLevel(level)

    unittest.main()



if __name__ == "__main__":
    main()
