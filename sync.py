#!/bin/env python3

from rackspace import Account, Accounts
from rackspace import Alias, Aliases, Spam
from rackspace import Api

import argparse
import json
import os
import time
import yaml

CONFIG_FILE = 'conf.yml'
CONFIG_DIR  = 'conf.d'
DEBUG = False

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

def process_accounts(cfg_accounts, rs_accounts):
    print('- Accounts(process)')
    for name, account in cfg_accounts.items():

        if name not in rs_accounts:
            account.add()

        else:
            diff = account.diff(rs_accounts[name])
            if len(diff):
                account.update(diff)

        if getattr(account, 'data') and 'spam' in account.data:
            process_spam(account.api, account.data['spam'], name=name)

    for name, account in rs_accounts.items():
        if name not in cfg_accounts:
            account.remove()

def process_aliases(cfg_aliases, rs_aliases):
    print('- Aliases(process)')
    for name, alias in cfg_aliases.items():

        if name not in rs_aliases:
            alias.add()

        else:
            diff = alias.diff(rs_aliases[name])
            if diff['changes']:
                alias.replace()

    for name, alias in rs_aliases.items():
        if name not in cfg_aliases:
            alias.remove()

def process_spam(api, data, name=None):
    if name is None:
        print(f'- Spam {api.domain}')
    else:
        print(f'- Spam {name}@{api.domain}')
    cfg_spam = Spam(api=api, data=data, name=name, debug=DEBUG)
    rs_spam = cfg_spam.get()

    if cfg_spam != rs_spam:
        diff = cfg_spam.diff(rs_spam)
        cfg_spam.set(diff)

def process_domain(domain, data, api):
    api.set_domain(domain)

    print(domain)

    if 'spam' in data:
        process_spam(api, data['spam'])

    if 'accounts' in data:
        print('- Accounts/Aliases(get)')
        accounts, aliases = _init_accounts(domain, data['accounts'], api)

        process_accounts(accounts, Accounts(api, debug=DEBUG).get())
        process_aliases(aliases, Aliases(api, debug=DEBUG).get())

def sync():
    CONFIG = load_config()

    api = Api(**CONFIG)

    for domain, domain_cfg in CONFIG['domains'].items():

        if domain == 'XXXmoonlightimagery.com':
            continue

        process_domain(domain, domain_cfg, api)

def wait_for_change():
    while True:
        if not os.path.exists('changed'):
            time.sleep(1)
            continue
        os.remove('changed')
        break

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--watch', '-w', default=False, action='store_true')
    args = parser.parse_args()

    while True:
        if args.watch:
            wait_for_change()

        sync()

        if not args.watch:
            break
