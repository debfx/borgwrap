#!/usr/bin/env python3

import argparse
import datetime
import os
import subprocess
import sys
import yaml

global_subprocess_runner = None

class SubprocessRunner:

    def run(self, cmds, env, stdout):
        return subprocess.run(cmds, check=True, env=env, stdout=stdout, universal_newlines=True)

    def run_hook(self, hook):
        return subprocess.run(hook, shell=True, check=True)

class ConfigParser:

    def parse(self, filename):
        with open(filename) as f:
            return yaml.safe_load(f)

class CreateAction:

    def add_parser(self, subparsers):
        parser_create = subparsers.add_parser("create")
        parser_create.add_argument("--no-prune", action="store_true")
        parser_create.set_defaults(execution=self.execute)

    def execute(self, config, args):
        hooks_before(config, dry_run=args.dry_run)
        action_create(config, dry_run=args.dry_run)
        hooks_after(config, dry_run=args.dry_run)
        if not args.no_prune:
            action_prune(config, dry_run=args.dry_run)


class ListAction:

    def add_parser(self, subparsers):
        parser_list = subparsers.add_parser("list")
        parser_list.set_defaults(execution=self.execute)

    def execute(self, config, args):
        action_list(config)


class PruneAction:

    def add_parser(self, subparsers):
         parser_prune = subparsers.add_parser("prune")
         parser_prune.set_defaults(execution=self.execute)

    def execute(self, config, args):
        action_prune(config, dry_run=args.dry_run)


class CheckAgeAction:

    def add_parser(self, subparsers):
        parser_check_age = subparsers.add_parser("nagios-check-age")
        parser_check_age.add_argument("--max-age", type=int, required=True, help="Max age in hours")
        parser_check_age.add_argument("--min-size", type=int, help="Min backup size in MiB")
        parser_check_age.set_defaults(execution=self.execute)

    def execute(self, config, args):
        if args.min_size:
            min_size = args.min_size * 1024 * 1024
        else:
            min_size = None
        action_check_age(config, max_age=args.max_age*3600, min_size=min_size)

def config_is_true(value):
    if isinstance(value, bool):
        return value
    elif isinstance(value, str) and value.lower() in ("yes", "true"):
        return True
    elif value == 1:
        return True
    else:
        return False


def run(action, config, archive=False, args=[], trailing_args=[], capture_stdout=False):
    repo = config["remote"]["repository"]
    if archive:
        repo += "::{}-{{utcnow:%Y-%m-%dT%H:%M:%SZ}}".format(config["remote"]["prefix"])

    env = dict(os.environ)
    if "rsh" in config["remote"]:
        env["BORG_RSH"] = config["remote"]["rsh"]

    if capture_stdout:
        stdout = subprocess.PIPE
    else:
        stdout = None

    cmds = ["borgbackup", action] + args + [repo] + trailing_args
    return global_subprocess_runner.run(cmds, env=env, stdout=stdout)


def action_create(config, dry_run):
    source = config["location"]["source"]
    if isinstance(source, str):
        source = [source]

    cmd = []

    if "compression" in config["remote"]:
        cmd += ["--compression", config["remote"]["compression"]]

    if "one_file_system" in config["location"] and config_is_true(config["location"]["one_file_system"]):
        cmd.append("--one-file-system")

    if "exclude_caches" in config["location"] and config_is_true(config["location"]["exclude_caches"]):
        cmd.append("--exclude-caches")

    if "exclude_if_present" in config["location"]:
        for exclude in config["location"]["exclude_if_present"]:
            cmd += ["--exclude-if-present", exclude]

    if "exclude" in config["location"]:
        for exclude in config["location"]["exclude"]:
            cmd += ["--exclude", exclude]

    if dry_run:
        cmd += ["--dry-run"]

    run("create", config, archive=True, args=cmd, trailing_args=source)


def action_list(config):
    run("list", config)


def action_check_age(config, max_age, min_size):
    proc_result = run("info", config, archive=False, args=["--last", "1", "--json"], capture_stdout=True)
    last_backup = yaml.safe_load(proc_result.stdout)

    backup_start = datetime.datetime.strptime(last_backup["archives"][0]["start"], "%Y-%m-%dT%H:%M:%S.%f")
    if (datetime.datetime.now() - backup_start).total_seconds() > max_age:
        print("BORGBACKUP WARNING: last backup too old\n\n{}".format(last_backup["archives"][0]["start"]))
        sys.exit(1)

    size = last_backup["archives"][0]["stats"]["original_size"]
    if min_size and size < min_size:
        print("BORGBACKUP WARNING: last backup too small\n\n{}B < {}B".format(size, min_size))
        sys.exit(1)

    print("BORGBACKUP OK")


def hooks_before(config, dry_run):
    if "hooks" not in config or "before" not in config["hooks"]:
        return

    for hook in config["hooks"]["before"]:
        if dry_run:
            print("Not running hook \"{}\" as dry run is enabled.".format(hook))
        else:
            global_subprocess_runner.run_hook(hook)


def hooks_after(config, dry_run):
    if "hooks" not in config or "after" not in config["hooks"]:
        return

    for hook in config["hooks"]["after"]:
        if dry_run:
            print("Not running hook \"{}\" as dry run is enabled.".format(hook))
        else:
            global_subprocess_runner.run_hook(hook)


def action_prune(config, dry_run):
    cmd =  ["--stats", "--list"]
    cmd += ["--prefix", config["remote"]["prefix"]]

    if dry_run:
        cmd += ["--dry-run"]

    if "keep_last" in config["retention"]:
        cmd += ["--keep-last", str(config["retention"]["keep_last"])]

    if "keep_within" in config["retention"]:
        cmd += ["--keep-within", str(config["retention"]["keep_within"])]

    if "keep_hourly" in config["retention"]:
        cmd += ["--keep-hourly", str(config["retention"]["keep_hourly"])]

    if "keep_daily" in config["retention"]:
        cmd += ["--keep-daily", str(config["retention"]["keep_daily"])]

    if "keep_weekly" in config["retention"]:
        cmd += ["--keep-weekly", str(config["retention"]["keep_weekly"])]

    if "keep_monthly" in config["retention"]:
        cmd += ["--keep-monthly", str(config["retention"]["keep_monthly"])]

    if "keep_yearly" in config["retention"]:
        cmd += ["--keep-yearly", str(config["retention"]["keep_yearly"])]

    run("prune", config, args=cmd)


def main(subprocess_runner=SubprocessRunner(), config_parser=ConfigParser()):
    global global_subprocess_runner
    global global_config_parser
    global_subprocess_runner = subprocess_runner
    global_config_parser = config_parser

    parser = argparse.ArgumentParser(description="borgbackup wrapper.")
    parser.add_argument("--config", "-c", required=True)
    parser.add_argument("--dry-run", "-n", action="store_true")
    subparsers = parser.add_subparsers(dest="action")
    subparsers.required = True

    actions = [CreateAction(), ListAction(), PruneAction(), CheckAgeAction()]
    for action in actions:
        action.add_parser(subparsers)

    args = parser.parse_args()
    config = global_config_parser.parse(args.config)

    args.execution(config, args)
