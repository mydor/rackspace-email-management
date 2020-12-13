#!/bin/env python3

from rackspace import Account, Accounts
from rackspace import Alias, Aliases, Spam
from rackspace import Api

import json
import os
import yaml

CONFIG_FILE = 'conf.yml'
CONFIG_DIR  = 'conf.d'
DEBUG = False
#DEBUG = True

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

        #print(f'{domain} - {account}')
        if 'aliases' not in _acct_data:
            continue

        for _alias in _acct_data['aliases']:
            alias = _alias.replace(f'@{domain}', '')
            alias_lc = alias.lower()
            if alias not in aliases:
                aliases[alias_lc] = Alias(name=alias, address=email, api=api, debug=DEBUG)

            else:
                aliases[alias_lc].add_address(email)

            #print(f'-  {aliases[name]}')

    #print(accounts)
    #raise
    return accounts, aliases

def process_accounts(cfg_accounts, rs_accounts):
    print('- Accounts(process)')
    for name, account in cfg_accounts.items():

        if name not in rs_accounts:
            ### print(f'ADD: account {name}')
            account.add()

        else:
            diff = account.diff(rs_accounts[name])
            if len(diff):
                ### print(f'UPDATE: account {name}')
                ### print(f' - {diff}')
                account.update(diff)

        if getattr(account, 'data') and 'spam' in account.data:
            process_spam(account.api, account.data['spam'], name=name)

    for name, account in rs_accounts.items():
        if name not in cfg_accounts:
            ### print(f'DEL: account {name}')
            account.remove()

def process_aliases(cfg_aliases, rs_aliases):
    print('- Aliases(process)')
    for name, alias in cfg_aliases.items():

        if name not in rs_aliases:
            ### print(f'ADD: alias {name}')
            ### print(f'  - {cfg_aliases[name].addresses}')
            alias.add()

        else:
            diff = alias.diff(rs_aliases[name])
            if diff['changes']:
                ### print(f'UPDATE: alias {name}')
                ### print(f'  - {diff}')
                alias.replace()

    for name, alias in rs_aliases.items():
        if name not in cfg_aliases:
            ### print(f'DEL: alias {name}')
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

    #api.set_domain(domain)

    ### print(accounts)
    ### print('----------')
    ### print(Accounts(api).get())
    ### raise

if __name__ == '__main__':
    CONFIG = load_config()
    ### print(json.dumps(CONFIG, sort_keys=True, indent=4))

    api = Api(**CONFIG)

    for domain, domain_cfg in CONFIG['domains'].items():
        ### print(json.dumps(domain_cfg, sort_keys=True, indent=4))

        if domain == 'XXXmoonlightimagery.com':
            continue

        process_domain(domain, domain_cfg, api)
