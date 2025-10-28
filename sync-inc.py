#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import yaml

from rackspace import spam, Api, Account, Alias

KEYS = ['account', 'alias', 'spam', 'blocklist', 'ipblocklist', 'safelist', 'ipsafelist']
REMOVE = ('account', 'alias')

SYNC_DIR = 'state'
CONFIG_FILE = 'conf.yml'

api = None

def split(fname):
    basename = os.path.basename(fname)

    items = basename.split('-')
    _type = items[-1]

    addr = '-'.join(items[:-1])

    name, domain = addr.split('@')
    if name == '':
        name = None

    api.domain = domain

    if _type == 'account':
        obj = Account(api=api, name=name)
    elif _type == 'alias':
        obj = Alias(api=api, name=name)
    elif _type == 'spam':
        obj = spam.Settings(api=api, name=name)
    elif _type == 'blocklist':
        obj = spam.ACL(api=api, acl='blocklist', name=name)
    elif _type == 'ipblocklist':
        obj = spam.ACL(api=api, acl='ipblocklist', name=name)
    elif _type == 'safelist':
        obj = spam.ACL(api=api, acl='safelist', name=name)
    elif _type == 'ipsafelist':
        obj = spam.ACL(api=api, acl='ipsafelist', name=name)

    return addr, obj

def save_md5(fname, md5, debug=True):
    if not debug:
        with open(f'{fname}.md5', 'w') as fh:
            fh.write(md5)

def sync(fname, data):
    print(f'SYNC: {fname}')

    addr, local_object = split(fname)

    local_object.load(data=data['json'])
    online_object = local_object.get()

    if online_object is None or ( hasattr(online_object, 'success') and not online_object.success ):
        print('NEW')
        # new
        if getattr(local_object, 'add', None) is not None:  # Account, Alias
            print('obj.add()')
            local_object.add(recover=online_object.canRecover)
            return save_md5(fname, data['md5'], debug=False)

        elif getattr(local_object, 'set', None) is not None: # spam.Settings, spam.ACL
            print('obj.set()')
            local_object.set()
            return save_md5(fname, data['md5'], debug=False)

        return

    else:
        diff = local_object.diff(online_object)
        if diff is None:
            return save_md5(fname, data['md5'], debug=False)

        elif 'changes' in diff:
            if diff['changes'] > 0:
                print(f'1: obj.update({diff})')
                local_object.update(diff)
                return save_md5(fname, data['md5'], debug=False)

            else:
                return save_md5(fname, data['md5'], debug=False)

        elif len(diff) > 0:
            print(f'2: obj.update({diff})')
            local_object.update(diff)
            return save_md5(fname, data['md5'], debug=False)

        else:
            return save_md5(fname, data['md5'], debug=False)

def remove(fname):
    print(f'REMOVE: {fname}')

    addr, obj = split(fname)

    return_state = obj.get()
    if getattr(return_state, 'remove', None) is not None:
        return_state.remove()
        os.unlink(f'{fname}.md5')

def cfg(cfg_name):
    with open(cfg_name) as fh:
        raw = fh.read()

    data = yaml.safe_load(raw)

    global api
    api = Api(user_key=data['user_key'], secret_key=data['secret_key'], customer_id=data['customer_id'])
    #print(api)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', '-d', default=SYNC_DIR)
    parser.add_argument('--conf', '-c', default=CONFIG_FILE)
    args = parser.parse_args()

    cfg(args.conf)

    settings = {k: {} for k in KEYS}
    cksum = {k: {} for k in KEYS}

    # build data
    for path, dirs, files in os.walk(args.data):
        if os.path.dirname(path) == args.data:
            continue

        for fname in files:
            if fname.startswith('.'):
                continue

            filepath = os.path.join(path, fname)
            basename, ext = os.path.splitext(filepath)
            _type = basename.split('-')[-1]

            with open(filepath, 'r') as fh:
                data = fh.read()

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
