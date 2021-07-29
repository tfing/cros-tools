#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This is a tool for picking patches from upstream and applying them."""

"""echo""" "This is a python script! Don't interpret it with bash."
"""exit"""

import argparse
from collections import OrderedDict
import configparser
import functools
import mailbox
import os
import pprint
import re
import signal
import socket
import ssl
import subprocess
import sys
import textwrap
import urllib.request
import xmlrpc.client
import requests
import json
import pathlib
from pygerrit2 import GerritRestAPI, HTTPBasicAuth, Anonymous
from datetime import datetime

errprint = functools.partial(print, file=sys.stderr)

CROS_PATH='/proj/mtk15399/cros'
CHERRY = {
        'atf':
        { 'change_id':2780815, 'path':'/src/third_party/arm-trusted-firmware'},
        'blob':
        { 'change_id':2719722, 'path':'/src/third_party/coreboot/3rdparty/blobs'},
        'coreboot':
        { 'change_id':2658525, 'path':'/src/third_party/coreboot'},
        'depthcharge':
        { 'change_id':2721390, 'path':'/src/platform/depthcharge'},
        'ec':
        { 'change_id':2730643, 'path':'/src/platform/ec'},
        'kernel':
        { 'change_id':2781499, 'path':'/src/third_party/kernel/v5.10'},
        'vboot':
        { 'change_id':2772411, 'path':'/src/platform/vboot_reference'},
}

def _git(args, stdin=None, encoding='utf-8', no_stderr=False):
    """Calls a git subcommand.

    Similar to subprocess.check_output.

    Args:
        args: subcommand + args passed to 'git'.
        stdin: a string or bytes (depending on encoding) that will be passed
            to the git subcommand.
        encoding: either 'utf-8' (default) or None. Override it to None if
            you want both stdin and stdout to be raw bytes.
        no_stderr: If True, we'll eat stderr

    Returns:
        the stdout of the git subcommand, same type as stdin. The output is
        also run through strip to make sure there's no extra whitespace.

    Raises:
        subprocess.CalledProcessError: when return code is not zero.
            The exception has a .returncode attribute.
    """
    return subprocess.run(
        ['git'] + args,
        encoding=encoding,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=(subprocess.PIPE if no_stderr else None),
        check=True,
    ).stdout.strip()

def gen_fetch_link(change_id):
    url = 'https://chromium-review.googlesource.com'
    cmd=f'/changes/{change_id}?o=CURRENT_REVISION'

    auth = Anonymous()
    rest = GerritRestAPI(url=url, auth=auth)
    try:
        changes = rest.get(cmd)
    except requests.exceptions.HTTPError as e:
        print(e)
        print('=> Invalid change_id')
        exit()

    #  print(json.dumps(changes, indent=4, sort_keys=True))

    revision = changes['revisions'][changes['current_revision']]
    rev_num = revision['_number']
    url = revision['fetch']['http']['url']
    ref = revision['fetch']['http']['ref']

    return [url, ref, rev_num]

def checkout_current_revision(change_id, branch=''):

    url,ref,rev_num = gen_fetch_link(change_id)

    if branch == None:
        timestamp = datetime.now().strftime('%m%d-%H%M')
        br = f'{change_id}-{rev_num}-{timestamp}'
    else:
        br = f'{change_id}-{rev_num}-{branch}'

    # example: git fetch https://chromium.googlesource.com/chromiumos/third_party/kernel refs/changes/99/2781499/82 && git checkout -b change-2781499 FETCH_HEAD
    print(f'>>>> fetch {url} {ref}')
    out = _git(['fetch', f'{url}', f'{ref}'])
    print(out)

    print(f'>>>> checkout branch {br}')
    out = _git(['checkout', 'FETCH_HEAD', '-b', f'{br}'])
    print(out)

def pick_current_revision(change_id):

    url,ref,rev_num = gen_fetch_link(change_id)

    # example: git fetch https://chromium.googlesource.com/chromiumos/third_party/kernel refs/changes/37/3056237/1 && git cherry-pick FETCH_HEAD
    print(f'>>>> fetch {url} {ref}')
    out = _git(['fetch', f'{url}', f'{ref}'])
    print(out)

    print(f'>>>> cherry-pick {change_id}')
    out = _git(['cherry-pick', 'FETCH_HEAD'])
    print(out)

def checkout_target(change_id, branch_postfix):
    print('>>>> input')
    print(f'change_id {change_id}')
    print(f'branch postfix {branch_postfix}')

    print('>>>> git status')
    try:
        ret = _git(['status'])
        print(ret)
    except subprocess.CalledProcessError:
        exit()

    checkout_current_revision(change_id, branch_postfix)


def pick_target(change_id):
    print('>>>> input')
    print(f'change_id {change_id}')

    print('>>>> git status')
    try:
        ret = _git(['status'])
        print(ret)
    except subprocess.CalledProcessError:
        exit()

    pick_current_revision(change_id)

def main(args):
    """This is the main entrypoint for fromupstream.

    Args:
        args: sys.argv[1:]

    Returns:
        An int return code.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('target', 
                        help='tot name or change id. tot names are '
                        'all, atf, blob, coreboot, depthcharge, ec, kernel '
                        'and vboot.')
    parser.add_argument('-b', '--branch', 
                        help="custom branch postfix. default is timestamp.")
    parser.add_argument('-p', '--pick', action="store_true",
                        help='change action from checkout to cherry-pick. '
                        'only available when target is change id.')

    args = parser.parse_args(args)

    #  print('target', args.target)

    pick = args.pick
    if pick:
        print(f'cherry-pick {args.target}...')
    else:
        print(f'checkout {args.target}...')

    branch_postfix = args.branch
    if args.branch:
        branch_postfix = args.branch

    change_id = 0
    tot_name = None
    try: 
        change_id = int(args.target)
        if pick:
            pick_target(change_id)
        else:
            checkout_target(change_id, branch_postfix)
    except ValueError:
        if pick:
            print('Error: cannot use --pick with tot name')
            exit()

        tot_name = args.target
        if tot_name not in CHERRY and tot_name != 'all':
            print('Error: Unknown tot name', tot_name)
            exit()

        if tot_name == 'all':
            for name, cfg in CHERRY.items():
                print('\n>>>> checkout', name)
                change_id = cfg['change_id']

                git_path = f'{CROS_PATH}{cfg["path"]}'
                os.chdir(git_path)

                checkout_target(change_id, branch_postfix)
        else:
            change_id = CHERRY[tot_name]['change_id']

            git_path = f'{CROS_PATH}{CHERRY[tot_name]["path"]}'
            os.chdir(git_path)

            checkout_target(change_id, branch_postfix)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
