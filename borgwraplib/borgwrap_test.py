#!/usr/bin/env python3

import unittest
import app
import sys
import collections
from unittest.mock import patch

class SubprocessRunnerSpy:

    def __init__(self):
        self.cmds = []
        self.hook = []

    def run(self, cmds, env, stdout):
        self.cmds.append(cmds)
        return 0

    def run_hook(self, hook):
        self.hook.append(hook)
        return 0


class ConfigParserSpy:

    def __init__(self):
        filename = None

    def parse(self, filename):
        self.filename = filename

        test_config = collections.defaultdict(dict)
        test_config['location']['source'] = ['source1', 'source2']
        test_config['remote']['repository'] = "/path/testrepo"
        test_config['remote']['prefix'] = "testprefix"
        return test_config


class BorgwrapTest(unittest.TestCase):

    def setUp(self):
        self.suprocess_runner_spy = SubprocessRunnerSpy()
        self.config_parser_spy = ConfigParserSpy()

    def run_app(self, argv):
        with patch.object(sys, 'argv', argv):
            app.main(self.suprocess_runner_spy, self.config_parser_spy)

    def test_list(self):
        self.run_app(["BorgwrapTest", "--config", "testconfigpath", "list"])

        self.assertEqual(self.config_parser_spy.filename, "testconfigpath")
        self.assertEqual(len(self.suprocess_runner_spy.cmds), 1)
        self.assertEqual(self.suprocess_runner_spy.cmds[0][0], "borgbackup")
        self.assertIn('list', self.suprocess_runner_spy.cmds[0])

    def test_create_with_prune(self):
        self.run_app(["BorgwrapTest", "--config", "testconfigpath", "create"])

        self.assertEqual(self.config_parser_spy.filename, "testconfigpath")
        self.assertEqual(len(self.suprocess_runner_spy.cmds), 2)
        self.assertListEqual(self.suprocess_runner_spy.cmds[0], ["borgbackup", "create", "/path/testrepo::testprefix-{utcnow:%Y-%m-%dT%H:%M:%SZ}", "source1", "source2"])
        self.assertListEqual(self.suprocess_runner_spy.cmds[1], ["borgbackup", "prune", "--stats", "--list", "--prefix", "testprefix", "/path/testrepo"])

    def test_create_without_prune(self):
        self.run_app(["BorgwrapTest", "--config", "testconfigpath", "create", "--no-prune"])

        self.assertEqual(self.config_parser_spy.filename, "testconfigpath")
        self.assertEqual(len(self.suprocess_runner_spy.cmds), 1)
        self.assertListEqual(self.suprocess_runner_spy.cmds[0], ["borgbackup", "create", "/path/testrepo::testprefix-{utcnow:%Y-%m-%dT%H:%M:%SZ}", "source1", "source2"])

    def test_prune(self):
        self.run_app(["BorgwrapTest", "--config", "testconfigpath", "prune"])

        self.assertEqual(self.config_parser_spy.filename, "testconfigpath")
        self.assertEqual(len(self.suprocess_runner_spy.cmds), 1)
        self.assertListEqual(self.suprocess_runner_spy.cmds[0], ["borgbackup", "prune", "--stats", "--list", "--prefix", "testprefix", "/path/testrepo"])


if __name__=='__main__':
    unittest.main(verbosity=2)
