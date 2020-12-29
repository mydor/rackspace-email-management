#!/usr/bin/env python3

### import hashlib
import glob
import yaml
import json
import os
import copy

SYNC_DIR = 'tmp'

def store(src, address, data):

    if len(data) < 1:
        return

    #fname = f'{src}-{address}'
    fname = f'{address}-{src}'

    #print(fname)
    target = os.path.join(SYNC_DIR, fname)

    json_data = json.dumps(data, sort_keys=True)
    with open(f'{target}.json', 'w') as fh:
        fh.write(json_data)
    ### md5 = hashlib.md5(json_data.encode())

    ### with open(f'{target}.md5', 'w') as fh:
    ###     fh.write(md5.hexdigest())

def parse_spam(domain, tmp_config, account=None):
    config = copy.deepcopy(tmp_config)
    if account is None:
        account=''

    for acl in ('blocklist', 'ipblocklist', 'safelist', 'ipsafelist'):
        if acl in config and len(config[acl]) > 0:
            store(acl, f'{account}@{domain}', sorted(list(set(config[acl]))))
            config.pop(acl)

    #fname = f'spam-{account}@{domain}'
    if 'settings' in config:
        store('spam', f'{account}@{domain}', config['settings'])

def parse_aliases(config):
    for alias in config:
        #fname = f'alias-{alias}'
        store('alias', alias, config[alias])

def parse_account(domain, tmp_config, account, aliases):
    config = copy.deepcopy(tmp_config)
    email = f'{account}@{domain}'

    if 'spam' in config:
        parse_spam(domain, config['spam'], account)
        config.pop('spam')

    if 'aliases' in config:
        for alias in config['aliases']:
            if alias not in aliases:
                aliases[alias] = [email]

            else:
                aliases[alias].append(email)
        config.pop('aliases')

    #fname = f'account-{account}@{domain}'
    store('account', email, config)

def parse_accounts(domain, config):
    aliases = {}
    for account, data in config.items():
        parse_account(domain, data, account, aliases)

    parse_aliases(aliases)

def parse_config(fname, domain):
    with open(fname, 'r') as fh:
        raw = fh.read()
    data = yaml.safe_load(raw)
    for k,v in data.items():
        if k == 'spam':
            parse_spam(domain, v)

        elif k == 'accounts':
            parse_accounts(domain, v)


# Remove files before recreating them
for fname in glob.glob(f'{SYNC_DIR}/*.json'):
    os.unlink(fname)

#conf.d
#[]
#['arch-mage.com.yml', 'domain.com.yml.dist', 'moonlightimagery.biz.yml', 'moonlightimagery.com.yml']
for path, dirs, files in os.walk('conf.d'):
    for fname in files:
        if not fname.endswith('.yml'):
            continue
        filepath = os.path.join(path, fname)
        (domain, ext) = os.path.splitext(fname)

        parse_config(filepath, domain)

