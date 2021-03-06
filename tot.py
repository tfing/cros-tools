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

BOARD = ''
CORSOLA = {
        'kernel':
        { 'change_id':3290835, 'path':'/src/third_party/kernel/v5.15'},
        'sof':
        { 'change_id':3423986, 'path':'/src/third_party/kernel/v5.15'},
}
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
        'debug':
        { 'change_id':3281584, 'path':'/src/third_party/kernel/v5.10'},
}

FW_TOTS = ['atf', 'blob', 'coreboot', 'depthcharge', 'vboot']

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

def modify_ref_version(ref, current_rev, target_rev):
    ret_ref = ref
    ret_rev = current_rev
    if target_rev <= current_rev:
        ret_rev = target_rev
        ret_ref = ref[:ref.rfind(str(current_rev))] + str(target_rev)
    elif target_rev != 9999:
        ret_ref = ''
        print(f'Error: {target_rev} exceeds latest revision {current_rev}')

    return [ret_ref, ret_rev]

def checkout_revision(change_id, branch='', patchset=9999):

    url,ref,rev_num = gen_fetch_link(change_id)

    target_ref, target_rev = modify_ref_version(ref, rev_num, patchset)
    if target_ref == '':
        return 

    timestamp = datetime.now().strftime('%m%d-%H%M')
    if branch == None:
        br = f'{change_id}-{target_rev}-{timestamp}'
    else:
        br = f'{change_id}-{target_rev}-{timestamp}-{branch}'

    # example: git fetch https://chromium.googlesource.com/chromiumos/third_party/kernel refs/changes/99/2781499/82 && git checkout -b change-2781499 FETCH_HEAD
    print(f'>>>> fetch {url} {target_ref}')
    out = _git(['fetch', f'{url}', f'{target_ref}'])
    print(out)

    print(f'>>>> checkout branch {br}')
    out = _git(['checkout', 'FETCH_HEAD', '-b', f'{br}'])
    print(out)

def pick_revision(change_id, patchset):

    url,ref,rev_num = gen_fetch_link(change_id)

    target_ref, target_rev = modify_ref_version(ref, rev_num, patchset)
    if target_ref == '':
        return

    # example: git fetch https://chromium.googlesource.com/chromiumos/third_party/kernel refs/changes/37/3056237/1 && git cherry-pick FETCH_HEAD
    print(f'>>>> fetch {url} {target_ref}')
    out = _git(['fetch', f'{url}', f'{target_ref}'])
    print(out)

    print(f'>>>> cherry-pick {change_id}')
    out = _git(['cherry-pick', 'FETCH_HEAD'])
    print(out)

def update_checkout_main_branch():

    print(f'>>>> update and checkout main')
    out = _git(['remote', 'update'])
    print(out)
    out = _git(['checkout', 'm/main'])
    print(out)

def checkout_target(change_id, branch_postfix, patchset):
    print('>>>> input')
    print(f'change_id {change_id} patchset {patchset}')
    print(f'branch postfix {branch_postfix}')

    print('>>>> git status')
    try:
        ret = _git(['status'])
        print(ret)
    except subprocess.CalledProcessError:
        exit()

    checkout_revision(change_id, branch_postfix, patchset)

def checkout_main():
    print('>>>> git status')
    try:
        ret = _git(['status'])
        print(ret)
    except subprocess.CalledProcessError:
        exit()

    update_checkout_main_branch()


def pick_target(change_id, patchset):
    print('>>>> input')
    print(f'change_id {change_id}')

    print('>>>> git status')
    try:
        ret = _git(['status'])
        print(ret)
    except subprocess.CalledProcessError:
        exit()

    pick_revision(change_id, patchset)

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
                        'atf, blob, coreboot, depthcharge, ec, debug, kernel '
                        'and vboot. tot group name is fw.')
    parser.add_argument('-d', '--board', default="corsola",
                        help='board name, {cherry, default=corsola}')
    parser.add_argument('-b', '--branch', 
                        help="custom branch postfix. default is timestamp.")
    parser.add_argument('-p', '--pick', action="store_true",
                        help='change action from checkout to cherry-pick. '
                        'only available when target is change id.')
    parser.add_argument('-v', '--revision', 
                        help="checkout specific patchset. default is latest.")

    args = parser.parse_args(args)

    #  print('target', args.target)

    #  print('board', args.board)
    if args.board == 'cherry':
        BOARD = CHERRY
    elif args.board == 'corsola':
        BOARD = CORSOLA
    else:
        print('Error: unknown board name:', args.board)
        exit()

    pick = args.pick
    if pick:
        print(f'cherry-pick {args.target}...')
    else:
        print(f'checkout {args.target}...')

    branch_postfix = args.branch

    patchset = 9999
    if args.revision:
        patchset = int(args.revision)
        print(f'checkout patchset {patchset}...')

    change_id = 0
    tot_name = None
    try: 
        change_id = int(args.target)
        if pick:
            pick_target(change_id, patchset)
        else:
            checkout_target(change_id, branch_postfix, patchset)
    except ValueError:
        if pick:
            print('Error: cannot use --pick with tot name')
            exit()

        tot_name = args.target
        if tot_name not in BOARD and tot_name != 'fw':
            print('Error: Unknown tot name', tot_name)
            exit()

        if tot_name == 'fw':
            for name in FW_TOTS:
                print('\n>>>> checkout', name)
                change_id = BOARD[name]['change_id']

                git_path = f'{CROS_PATH}{BOARD[name]["path"]}'
                os.chdir(git_path)

                #  checkout_target(change_id, branch_postfix, patchset)
                checkout_main()
        else:
            change_id = BOARD[tot_name]['change_id']

            git_path = f'{CROS_PATH}{BOARD[tot_name]["path"]}'
            os.chdir(git_path)

            # append branch name to easily identify it
            if branch_postfix == None:
                branch_postfix = tot_name

            checkout_target(change_id, branch_postfix, patchset)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
