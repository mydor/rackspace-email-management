#!/usr/bin/env python3
"""Full syncronize mail config with RackSpace"""

import argparse
import copy
import hashlib
import json
import os
import pathlib
# import time
import typing
import yaml

from rackspace import Account, Accounts
from rackspace import Alias, Aliases, Spam
from rackspace import Api

CONFIG_FILE = 'conf.yml'
CONFIG_DIR  = 'conf.d'
SYNC_DIR    = 'tmp'
DEBUG = False
ACCOUNT_FIELDS = ('firstName', 'lastName', 'displayName', 'enabled', 'password')

def load_md5(fname: str) -> str:
    """
    Load MD5 checksum from file

    Args:
        fname(str): Filename to load MD5 checksum from

    Returns:
        str: the MD5 checksum string
    """
    with open(fname, 'rt', encoding='utf-8') as fh:
        md5 = fh.read()

    return md5

def save_md5( # pylint: disable=unused-argument
        target: str,
        md5: str,
        debug: typing.Optional[bool] =False) -> None:
    """
    Save MD5 checksum to file

    Args:
        target(str): Filename (without extension)
        md5(str): MD5 checksum string to save
        debug(bool, optional): Debug flag

    Returns:
        None
    """
    # Don't overwrite if the data hasn't changed, preserves the timestamp
    # of the file, showing the last time it was updated
    md5_file = f'{target}.md5'

    try:
        if load_md5(md5_file) == md5:
            return
    except FileNotFoundError:
        pass

    with open(md5_file, 'wt', encoding='utf-8') as fin:
        fin.write(md5)

def save_json( # pylint: disable=unused-argument
        target: str,
        json_data: str,
        debug: typing.Optional[bool] =False) -> None:
    """
    Save JSON data to file

    Args:
        target(str): Filename (without extension)
        json_data(str): JSON data string to save
        debug(bool, optional): Debug flag

    Returns:
        None
    """
    json_file = f'{target}.json'

    with open(json_file, 'wt', encoding='utf-8') as fout:
        fout.write(json_data)

def store(src: str,
          address: str,
          data: dict,
          data_dir: str,
          debug: typing.Optional[bool] =False) -> None:
    """
    Store mail element settings

    Args:
        src(str): Data type (account, alias, etc)
        address(str): Email address of element to store
        data(dict): Mail element data to store
        data_dir(str): Path of sync directory
        debug(bool, optional): Debug flag

    Returns:
        None
    """
    if len(data) < 1:
        return

    target = os.path.join(data_dir, f'{"." if debug else ""}{address}-{src}')

    json_data = json.dumps(data, sort_keys=True)
    save_json(target, json_data)

    md5 = hashlib.md5(json_data.encode()).hexdigest()
    save_md5(target, md5)

def load_config(
        name: typing.Optional[str] =None) -> dict:
    """
    Load config

    Args:
        name(str, optional): Config filename

    Returns:
        dict: Full config as dictionary
    """
    if name is None:
        name = CONFIG_FILE

    with open(name, 'rt', encoding='utf-8') as fin:
        raw = fin.read()

    data = yaml.safe_load(raw)

    if 'domains' in data:
        domains = {}

        for domain in data['domains']:
            domain_file = f'{os.path.join(data.get("conf_dir", CONFIG_DIR), domain)}.yml'
            # domain_file = '{}.yml'.format(os.path.join(data.get('conf_dir', CONFIG_DIR), domain))
            domain_data = load_config(domain_file)
            domains[domain] = domain_data

        data['domains'] = domains

    return data

def init_accounts(
        domain: str,
        data: dict,
        api: Api) -> typing.Tuple[dict, dict]:
    """
    Initialize account data for processing

    Args:
        domain(str): Domain name of accounts
        data(dict): Configuration data of accounts
        api(Api): API object

    Returns:
        tuple:
            dict: accounts
            dict: aliases
    """
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

def store_account(account: dict) -> None:
    """
    Store account data

    Args:
        account(dict): Account data

    Returns:
        None
    """
    data = {}
    for field in ACCOUNT_FIELDS:
        if field in account.data:
            data[field] = account.data[field]

    store('account', account.name, data, SYNC_DIR, debug=DEBUG)

def process_accounts( # pylint: disable=unused-argument
        cfg_accounts: dict,
        rs_accounts: dict,
        domain: str) -> None:
    """
    Process Account with RackSpace

    Args:
        cfg_accounts(dict): Local account config
        rs_accounts(dict): RackSpace account config
        domain(str): Domain name of account space

    Returns:
        None
    """
    print('- Accounts(process)')
    for name, account in cfg_accounts.items():
        # print(account)
        # Account({name: "michael.smith@moonlightimagery.com", displayName: "Michael Smith", enabled: "True", firstName: "Michael", lastName: "Smith", size: "25600", visibleInExchangeGAL: "True", visibleInRackspaceEmailCompanyDirectory: "True"}) # pylint: disable=line-too-long
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

def store_alias(
        alias: Alias,
        domain: str) -> None:
    """
    Store alias to file

    Args:
        alias(Alias): Alias object
        domain(str): Domain of alias

    Returns:
        None
    """
    email = '@'.join((alias.name, domain))
    store('alias', email, alias.data, SYNC_DIR, debug=DEBUG)

def process_aliases(
        cfg_aliases: dict,
        rs_aliases: dict,
        domain: str) -> None:
    """
    Process aliases with RackSpace

    Args:
        cfg_aliases(dict): Local aliases
        rs_aliases(dict): RackSpace aliases
        domain(str): Domain name of aliases

    Returns:
        None
    """
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

def store_spam(
        spam_type: str,
        account: str,
        data: dict) -> None:
    """
    Save spam settings to file

    Args:
        spam_type(str): Type of spam settings (settings or ACL)
        account(str): Account of spam settings
        data(dict): Spam settings of account

    Returns:
        None
    """
    if spam_type == 'settings':
        spam_type = 'spam'

    store(spam_type, account, data, SYNC_DIR, debug=DEBUG)

def process_spam(
        api: Api,
        data: dict,
        name: str =None) -> None:
    """
    Process spam settings

    Args:
        api(Api): Api object
        data(dict): Spam settings
        name(str, optional): Account name of spam settings

    Returns:
        None
    """
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

def process_domain(
        domain: str,
        data: dict,
        api: Api) -> None:
    """
    Process domain settings (accounts, aliases, etc)

    Args:
        domain(str): Domain name being processed
        data(dict): Domain data
        api(Api): Api object

    Returns:
        None
    """
    api.set_domain(domain)

    print(f'DOMAIN: {domain}')

    if 'spam' in data:
        process_spam(api, data['spam'])

    if 'accounts' in data:
        print('- Accounts/Aliases(get)')
        accounts, aliases = init_accounts(domain, data['accounts'], api)

        process_accounts(accounts, Accounts(api, debug=DEBUG).get(), domain)
        process_aliases(aliases, Aliases(api, debug=DEBUG).get(), domain)

def sync(config: dict) -> None:
    """
    Sync mail settings with RackSpace

    Args:
        config(dict): Full config data

    Returns:
        None
    """
    api = Api(**config)

    for domain, domain_cfg in config['domains'].items():

        if domain == 'XXXmoonlightimagery.com':
            continue

        process_domain(domain, domain_cfg, api)

# def wait_for_change(
#         args: argparse.Namespace,
#         config: str) -> dict:
#     """
#     Monitor for config changes  *** NOT IMPLEMENTED ***

#     Args:
#         args(argparse.Namespace): Command line switches
#         config(str): Full config data

#     Returns:
#         dict:
#     """
#     change_file = os.path.join(args.dir, ('changed'))
#     while True:
#         if not os.path.exists(change_file):
#             time.sleep(1)
#             continue

#         os.remove(change_file)
#         break

#     return load_config(args.conf)

def main() -> None:
    """Main entry point"""
    # pylint: disable=duplicate-code
    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', '-c',
                        help="Config file",
                        type=pathlib.Path,
                        metavar='<FILE>',
                        default=CONFIG_FILE)
    parser.add_argument('--data', '-d',
                        help="Where supplemental config files are stored",
                        type=pathlib.Path,
                        metavar='<DIR>',
                        default=SYNC_DIR)

    parser.add_argument('--watch', '-w', default=False, action='store_true')
    # parser.add_argument('--dir', '-d', default=CONFIG_DIR)
    # parser.add_argument('--conf', '-c', default=CONFIG_FILE)
    args = parser.parse_args()

    if not os.path.exists(args.conf):
        args.conf = os.path.join(args.dir, args.conf)

    config = load_config(args.conf)
    sync(config)

    # while True: # for watcher
    #     if args.watch:
    #         config = wait_for_change(args, config)

    #     sync(config)

    #     if not args.watch:
    #         break

if __name__ == '__main__':
    main()
