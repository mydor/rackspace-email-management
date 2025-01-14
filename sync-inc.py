#!/usr/bin/env python3
# pylint: disable=invalid-name
"""
Syncronize mail config incrementally
"""
import argparse
import hashlib
import json
import os
import pathlib
import typing
import yaml

from typing import Optional, Union, Tuple

from rackspace import spam, Api, Account, Alias

KEYS = ['account', 'alias', 'spam', 'blocklist', 'ipblocklist', 'safelist', 'ipsafelist']
REMOVE = ('account', 'alias')

SYNC_DIR = 'tmp'
CONFIG_FILE = 'conf.yml'

API = None

InitObj = Tuple[
    str,
    Union[
        Account,
        Alias,
        spam.Settings,
        spam.ACL
    ]
]

def init_obj(fname: str) -> InitObj:
    """
    Initialize an empty mail object from a file

    Args:
        fname(str): Filename to load object from

    Returns:
        tuple:
            str: email address
            object: Account, Alias, spam.Settings or spam.ACL object
    """
    basename = os.path.basename(fname)

    items = basename.split('-')
    obj_type = items[-1]

    addr = '-'.join(items[:-1])

    name: Optional[str]
    domain: str
    name, domain = addr.split('@')
    if name == '':
        name = None

    API.domain = domain

    if obj_type == 'account':
        obj = Account(api=API, name=name)
    elif obj_type == 'alias':
        obj = Alias(api=API, name=name)
    elif obj_type == 'spam':
        obj = spam.Settings(api=API, name=name)
    elif obj_type == 'blocklist':
        obj = spam.ACL(api=API, acl='blocklist', name=name)
    elif obj_type == 'ipblocklist':
        obj = spam.ACL(api=API, acl='ipblocklist', name=name)
    elif obj_type == 'safelist':
        obj = spam.ACL(api=API, acl='safelist', name=name)
    elif obj_type == 'ipsafelist':
        obj = spam.ACL(api=API, acl='ipsafelist', name=name)

    return addr, obj

def save_md5(
        fname: str,
        md5: str,
        debug: typing.Optional[bool] =True) -> None:
    """
    Save the MD5 checksum

    Args:
        fname(str): filename to save MD5 checksum of/for
        md5(str): MD5 checksum to save
        debug(bool, optional): Debug flag

    Returns:
        None
    """
    if debug:
        return

    with open(f'{fname}.md5', 'wt', encoding='utf-8') as fout:
        fout.write(md5)

def sync(
        fname: str,
        data: dict) -> None:
    """
    Syncronize mail element from file

    Args:
        fname(str): Filename containing element to sync
        data(dict): Email element dictionary

    Returns:
        None
    """
    print(f'SYNC: {fname}')

    # addr, local_object = init_obj(fname)
    _, local_object = init_obj(fname)

    # Load our local config into the object
    local_object.load(data=data['json'])

    # Ask the object to get a new object with what
    # RackSpace thinks it shoule be
    online_object = local_object.get()

    if online_object is None or ( hasattr(online_object, 'success') and not online_object.success ):
        print('NEW')
        # new
        if getattr(local_object, 'add', None) is not None:  # Account, Alias
            print('obj.add()')
            local_object.add(recover=online_object.canRecover)
            save_md5(fname, data['md5'], debug=False)

        elif getattr(local_object, 'set', None) is not None: # spam.Settings, spam.ACL
            print('obj.set()')
            local_object.set()
            save_md5(fname, data['md5'], debug=False)

        return

    # Not a new mail element
    diff = local_object.diff(online_object)
    if diff is None:
        pass

    elif 'changes' in diff:
        if diff['changes'] > 0:
            print(f'1: obj.update({diff})')
            local_object.update(diff)

    elif len(diff) > 0:
        print(f'2: obj.update({diff})')
        local_object.update(diff)

    save_md5(fname, data['md5'], debug=False)

def remove(fname: str) -> None:
    """
    Remove object from RackSpace

    Args:
        fname(str): filename of sync object

    Returns:
        None
    """
    print(f'REMOVE: {fname}')

    # addr, obj = init_obj(fname)
    _, local_obj = init_obj(fname)

    online_obj = local_obj.get()
    if getattr(online_obj, 'remove', None) is not None:
        online_obj.remove()
        os.unlink(f'{fname}.md5')

def load_cfg(cfg_name: str) -> None:
    """
    Read base config for API settings

    Args:
        cfg_name(str): Config file to load

    Returns:
        None
    """
    with open(cfg_name, 'rt', encoding='utf-8') as fin:
        raw = fin.read()

    data = yaml.safe_load(raw)

    global API # pylint: disable=global-statement
    API = Api(user_key=data['user_key'],
              secret_key=data['secret_key'],
              customer_id=data['customer_id'])
    #print(API)

def main() -> None: # pylint: disable=too-many-locals
    """Main entry point"""
    # pylint: disable=duplicate-code
    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', '-c',
                        help="Config file",
                        type=pathlib.Path,
                        metavar='<FILE>',
                        default=CONFIG_FILE)
    parser.add_argument('--data', '-d',
                        help="Where sync files are stored",
                        type=pathlib.Path,
                        metavar='<DIR>',
                        default=SYNC_DIR)
    # parser.add_argument('--data', '-d', default=SYNC_DIR, help="Config directory")
    # parser.add_argument('--conf', '-c', default=CONFIG_FILE, help="Where sync files are stored")
    args = parser.parse_args()

    load_cfg(args.conf)

    settings = {k: {} for k in KEYS}
    cksum = {k: {} for k in KEYS}

    # build data
    for path, _, files in os.walk(args.data):
        if os.path.dirname(path) == args.data:
            continue

        for fname in files:
            # Skip hidden
            if fname.startswith('.'):
                continue

            filepath = os.path.join(path, fname)
            basename, ext = os.path.splitext(filepath)
            _type = basename.split('-')[-1]

            with open(filepath, 'rt', encoding='utf-8') as fin:
                data = fin.read()

            if ext == '.md5':
                cksum[_type].update({basename: {'md5': data}})

            elif ext == '.json':
                md5 = hashlib.md5(data.encode()).hexdigest()
                settings[_type].update({basename: {'json': json.loads(data), 'md5': md5}})

    for _type in KEYS:
        cfg = settings[_type]
        md5 = cksum[_type]

        keys = list(cfg)
        for fpath in keys:

            if fpath not in md5 or cfg[fpath]['md5'] != md5[fpath]['md5']:
                sync(fpath, cfg[fpath])

            cfg.pop(fpath)
            if fpath in md5:
                md5.pop(fpath)

        if _type not in REMOVE:
            continue

        keys = list(md5)
        for fpath in keys:
            remove(fpath)

if __name__ == '__main__':
    main()
