#!/usr/bin/env python3

import argparse
import copy
import hashlib
import json
import os
import time
import yaml

from rackspace import Account, Accounts
from rackspace import Alias, Aliases, Spam
from rackspace import Api

CONFIG_FILE = 'conf.yml'
CONFIG_DIR  = 'conf.d'
SYNC_DIR    = 'tmp'
DEBUG = False
ACCOUNT_FIELDS = ('firstName', 'lastName', 'displayName', 'enabled', 'password')

def load_md5(fname):
    with open(fname, 'r') as fh:
        md5 = fh.read()

    return md5

def save_md5(target, md5, debug=False):
    # Don't overwrite if the data hasn't changed, preserves the timestamp
    # of the file, showing the last time it was updated
    md5_file = f'{target}.md5'

    try:
        if load_md5(md5_file) == md5:
            return
    except FileNotFoundError:
        pass

    with open(md5_file, 'w') as fh:
        fh.write(md5)

def store(src, address, data, data_dir, debug=False):
    if len(data) < 1:
        return

    target = os.path.join(data_dir, f'{"." if debug else ""}{address}-{src}')

    json_data = json.dumps(data, sort_keys=True)

    with open(f'{target}.json', 'w') as fh:
        fh.write(json_data)

    md5 = hashlib.md5(json_data.encode()).hexdigest()
    save_md5(target, md5)

def load_config(name=None):
    if name is None:
        name = CONFIG_FILE

    with open(name, 'r') as fh:
        raw = fh.read()

    data = yaml.safe_load(raw)

    if 'domains' in data:
        domains = {}

        for domain in data['domains']:
            domain_file = '{}.yml'.format(os.path.join(data.get('conf_dir', CONFIG_DIR), domain))
            domain_data = load_config(domain_file)
            domains[domain] = domain_data

        data['domains'] = domains

    return data

def _init_accounts(domain, data, api):
    accounts = {}
    aliases = {}

    for acct_name, _acct_data in data.items():
        email = f'{acct_name}@{domain}'

        account = Account(email, data=data[acct_name], api=api, debug=DEBUG)
        accounts.update({acct_name.lower(): account})

        if 'aliases' not in _acct_data:
            continue

        for _alias in _acct_data['aliases']:
            alias = _alias.replace(f'@{domain}', '')
            alias_lc = alias.lower()
            if alias not in aliases:
                aliases[alias_lc] = Alias(name=alias, address=email, api=api, debug=DEBUG)

            else:
                aliases[alias_lc].add_address(email)

    return accounts, aliases

def store_account(account):
    data = {}
    for field in ACCOUNT_FIELDS:
        if field in account.data:
            data[field] = account.data[field]

    store('account', account.name, data, SYNC_DIR, debug=DEBUG)

def process_accounts(cfg_accounts, rs_accounts, domain):
    print('- Accounts(process)')
    for name, account in cfg_accounts.items():
        # print(account)
        # Account({name: "michael.smith@moonlightimagery.com", displayName: "Michael Smith", enabled: "True", firstName: "Michael", lastName: "Smith", size: "25600", visibleInExchangeGAL: "True", visibleInRackspaceEmailCompanyDirectory: "True"})
        # {"firstName": "Michael", "lastName": "Smith"}

        if name not in rs_accounts:
            account.add()

        else:
            diff = account.diff(rs_accounts[name])
            if len(diff):
                account.update(diff)

        if getattr(account, 'data') and 'spam' in account.data:
            process_spam(account.api, account.data['spam'], name=name)

        store_account(account)

    for name, account in rs_accounts.items():
        if name not in cfg_accounts:
            account.remove()

def store_alias(alias, domain):
    email = '@'.join((alias.name, domain))
    store('alias', email, alias.data, SYNC_DIR, debug=DEBUG)

def process_aliases(cfg_aliases, rs_aliases, domain):
    print('- Aliases(process)')
    for name, alias in cfg_aliases.items():

        if name not in rs_aliases:
            alias.add()

        else:
            diff = alias.diff(rs_aliases[name])
            if diff['changes']:
                alias.replace()

        store_alias(alias, domain)

    for name, alias in rs_aliases.items():
        if name not in cfg_aliases:
            alias.remove()

def store_spam(_type, account, data):
    if _type == 'settings':
        _type = 'spam'

    store(_type, account, data, SYNC_DIR, debug=DEBUG)

def process_spam(api, data: dict, name: str =None):
    account = f'{"" if name is None else f"{name}"}@{api.domain}'

    print(f'- Spam {account}')

    cfg_spam = Spam(api=api, data=data, name=name, debug=DEBUG)
    rs_spam = cfg_spam.get()

    if cfg_spam != rs_spam:
        diff = cfg_spam.diff(rs_spam)
        cfg_spam.set(diff)

    types = ('blocklist', 'safelist', 'ipblocklist', 'ipsafelist', 'settings')

    spamdata = copy.deepcopy(data)
    for stype in types:
        if stype in spamdata:
            sdata = spamdata.pop(stype)

            if len(sdata):
                if isinstance(sdata, list):
                    sdata.sort()

                store_spam(stype, account, sdata)

def process_domain(domain, data, api):
    api.set_domain(domain)

    print(f'DOMAIN: {domain}')

    if 'spam' in data:
        process_spam(api, data['spam'])

    if 'accounts' in data:
        print('- Accounts/Aliases(get)')
        accounts, aliases = _init_accounts(domain, data['accounts'], api)

        process_accounts(accounts, Accounts(api, debug=DEBUG).get(), domain)
        process_aliases(aliases, Aliases(api, debug=DEBUG).get(), domain)

def sync(CONFIG):
    api = Api(**CONFIG)

    for domain, domain_cfg in CONFIG['domains'].items():

        if domain == 'XXXmoonlightimagery.com':
            continue

        process_domain(domain, domain_cfg, api)

def wait_for_change(args, CONFIG):
    change_file = os.path.join(args.dir, ('changed'))
    while True:
        if not os.path.exists(change_file):
            time.sleep(1)
            continue

        os.remove(change_file)
        break

    return load_config(args.conf)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--watch', '-w', default=False, action='store_true')
    parser.add_argument('--dir', '-d', default=CONFIG_DIR)
    parser.add_argument('--conf', '-c', default=CONFIG_FILE)
    args = parser.parse_args()

    if not os.path.exists(args.conf):
        args.conf = os.path.join(args.dir, args.conf)

    CONFIG = load_config(args.conf)

    while True:
        if args.watch:
            CONFIG = wait_for_change(args, CONFIG)

        sync(CONFIG)

        if not args.watch:
            break
