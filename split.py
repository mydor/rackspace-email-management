#!/usr/bin/env python3

import argparse
import copy
import glob
import json
import os
import yaml

CONFIG_DIR = 'conf.d'
SYNC_DIR = 'tmp'

def store(src, address, data, data_dir):

    if len(data) < 1:
        return

    fname = f'{address}-{src}'

    target = os.path.join(data_dir, fname)

    json_data = json.dumps(data, sort_keys=True)
    with open(f'{target}.json', 'w') as fh:
        fh.write(json_data)

def parse_spam(domain, tmp_config, args, account=None):
    config = copy.deepcopy(tmp_config)
    if account is None:
        account=''

    for acl in ('blocklist', 'ipblocklist', 'safelist', 'ipsafelist'):
        if acl in config and len(config[acl]) > 0:
            store(acl, f'{account}@{domain}', sorted(list(set(config[acl]))), data_dir=args.data)
            config.pop(acl)

    if 'settings' in config:
        store('spam', f'{account}@{domain}', config['settings'], data_dir=args.data)

def parse_aliases(config, args):
    for alias in config:
        store('alias', alias, config[alias], data_dir=args.data)

def parse_account(domain, tmp_config, account, aliases, args):
    config = copy.deepcopy(tmp_config)
    email = f'{account}@{domain}'

    if 'spam' in config:
        parse_spam(domain, config['spam'], args, account)
        config.pop('spam')

    if 'aliases' in config:
        for alias in config['aliases']:
            if alias not in aliases:
                aliases[alias] = [email]

            else:
                aliases[alias].append(email)

        config.pop('aliases')

    store('account', email, config, data_dir=args.data)

def parse_accounts(domain, config, args):
    aliases = {}
    for account, data in config.items():
        parse_account(domain, data, account, aliases, args)

    parse_aliases(aliases, args)

def parse_config(fname, domain, args):
    with open(fname, 'r') as fh:
        raw = fh.read()
    data = yaml.safe_load(raw)
    for k,v in data.items():
        if k == 'spam':
            parse_spam(domain, v, args)

        elif k == 'accounts':
            parse_accounts(domain, v, args)

def cleandir_md5(path):
    for fname in glob.glob(f'''{os.path.join(path, '*.md5')}'''):
        jsonfile = f"{os.path.splitext(fname)[0]}.json"
        if os.path.exists(jsonfile):
            continue

        os.unlink(fname)

def cleandir_json(path):
    for fname in glob.glob(f'''{os.path.join(path, '*.json')}'''):
        os.unlink(fname)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', default=CONFIG_DIR)
    parser.add_argument('--data', '-d', default=SYNC_DIR)
    args = parser.parse_args()

    # Remove files before recreating them, keeps obsolete files from building up
    # sync-inc.py will handle removing .md5 files without a corresponding .json file
    # but we need to clear .json to signify a mail object (account/alias/etc) was deleted
    cleandir_json(args.data)

    #conf.d
    #[]
    #['arch-mage.com.yml', 'domain.com.yml.dist', 'moonlightimagery.biz.yml', 'moonlightimagery.com.yml']
    for path, dirs, files in os.walk(args.config):
        for fname in files:
            if not fname.endswith('.yml'):
                continue
            filepath = os.path.join(path, fname)
            (domain, ext) = os.path.splitext(fname)

            parse_config(filepath, domain, args)

