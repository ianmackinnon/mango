#!/usr/bin/env python3

# pylint: disable=wrong-import-position,import-error
# Allow appending to import path before import
# Must also specify `PYTHONPATH` when invoking Pylint.

import os
import sys
import json
import logging
import argparse
import unittest

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
            print((name, known_result, result))
            self.assertIsInstance(result, str)
            self.assertEqual(known_result, result)



def main():
    LOG.addHandler(logging.StreamHandler())

    parser = argparse.ArgumentParser(
        description="Test short name (slug) function produces desired results.")
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
