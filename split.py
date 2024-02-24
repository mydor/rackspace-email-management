#!/usr/bin/env python3

"""
Load mail config and parse to "simple" constructs
that can by syncronized incrementally
"""
import argparse
import copy
import glob
import json
import os
import pathlib
import typing
import yaml

CONFIG_FILE = 'conf.yml'
CONFIG_DIR = 'conf.d'
SYNC_DIR = 'tmp'

def store(
        src: str,
        address: str,
        data: dict,
        data_dir: str) -> None:
    """
    Store a sync "object" as json to the sync directory

    Args:
        src(str): The source class of the object account, alias, etc
        address(str): The e-mail address of the object
        data(dict): The data to be stored
        data_dir(str): The directory to store the json file

    Returns:
        None
    """
    if len(data) < 1:
        return

    fname = f'{address}-{src}'

    target = os.path.join(data_dir, fname)

    json_data = json.dumps(data, sort_keys=True)
    with open(f'{target}.json', 'wt', encoding='utf-8') as fout:
        fout.write(json_data)

def parse_spam(
        domain: str,
        tmp_config: dict,
        args: argparse.Namespace,
        account: typing.Optional[str] =None) -> None:
    """
    Parse and save Spam settings

    Args:
        domain(str): domain name of account
        tmp_config(dict): Config dictionary to be deepcopied and not touched
        args(argparse.Namespace): command line switches
        account(str, optional): Account name (email)

    Returns:
        None
    """
    config = copy.deepcopy(tmp_config)
    if account is None:
        account=''

    for acl in ('blocklist', 'ipblocklist', 'safelist', 'ipsafelist'):
        if acl in config and len(config[acl]) > 0:
            store(acl, f'{account}@{domain}', sorted(list(set(config[acl]))), data_dir=args.sync)
            config.pop(acl)

    if 'settings' in config:
        store('spam', f'{account}@{domain}', config['settings'], data_dir=args.sync)

def parse_aliases(
        config: dict,
        args: argparse.Namespace) -> None:
    """
    Parse and save aliases

    Args:
        config(dict): Configuration of aliases
        args(argparse.Namespace): command line switches

    Returns:
        None
    """
    for alias in config:
        store('alias', alias, config[alias], data_dir=args.sync)

def parse_account(
        domain: str,
        tmp_config: dict,
        account: str,
        aliases: dict,
        args: argparse.Namespace) -> None:
    """
    Parse and save accounts

    Args:
        domain(str): Domain name of account
        tmp_config(dict): Config dictionary to be deepcopied and not touched
        account(str): Account (LHS of email)
        aliases(dict): Dictionary of aliases
        args(argparse.Namespace): command line switches

    Returns:
        None
    """
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

    store('account', email, config, data_dir=args.sync)

def parse_accounts(
        domain: str,
        config: dict,
        args: argparse.Namespace) -> None:
    """
    Parse configured accounts

    Args:
        domain(str): Domain name of account
        config(dict): Dictionary containing accounts to be parsed
        args(argparse.Namespace): command line switches

    Returns:
        None
    """
    aliases = {}
    for account, data in config.items():
        # Aliases is built while parsing accounts, because aliases
        # can point to multiple accounts
        parse_account(domain, data, account, aliases, args)

    parse_aliases(aliases, args)

def parse_config(
        fname: str,
        domain: str,
        args: argparse.Namespace) -> None:
    """
    Load and parse a config file

    Args:
        fname(str): Filename to load
        domain(str): Domain name we are parsing
        args(argparse.Namespace): Command line switches

    Returns:
        None
    """
    with open(fname, 'rt', encoding='utf-8') as fin:
        raw = fin.read()
    data = yaml.safe_load(raw)

    for key, val in data.items():
        if key == 'spam':
            parse_spam(domain, val, args)

        elif key == 'accounts':
            parse_accounts(domain, val, args)

# def cleandir_md5(path: str) -> None:
#     """
#     Remove dangling (checksum without a json) md5 files from sync directory

#     Args:
#         path(str): Path to the sync directory

#     Returns:
#         None
#     """
#     for fname in glob.glob(f'''{os.path.join(path, '*.md5')}'''):
#         jsonfile = f"{os.path.splitext(fname)[0]}.json"
#         if os.path.exists(jsonfile):
#             continue

#         os.unlink(fname)

def cleandir_json(path: str) -> None:
    """
    Remove json files in <path>

    Args:
        path(str): Path to remove json files from

    Returns:
        None
    """
    for fname in glob.glob(f'''{os.path.join(path, '*.json')}'''):
        os.unlink(fname)


def main() -> None:
    """Main entry point"""
    # pylint: disable=duplicate-code
    parser = argparse.ArgumentParser()
    parser.add_argument('--conf', '-c',
                        help="Config directory",
                        type=pathlib.Path,
                        metavar='<FILE>',
                        default=CONFIG_FILE)
    parser.add_argument('--data', '-d',
                        help="Where supplemental config files are stored",
                        type=pathlib.Path,
                        metavar='<DIR>',
                        default=CONFIG_DIR)
    parser.add_argument('--sync', '-s',
                        help="Where sync files are stored",
                        type=pathlib.Path,
                        metavar='<DIR>',
                        default=SYNC_DIR)
    args = parser.parse_args()

    # Remove files before recreating them, keeps obsolete files from building up
    # sync-inc.py will handle removing .md5 files without a corresponding .json file
    # but we need to clear .json to signify a mail object (account/alias/etc) was deleted
    cleandir_json(args.sync)

    #conf.d
    #[]
    #['arch-mage.com.yml', 'domain.com.yml.dist',
    # 'moonlightimagery.biz.yml', 'moonlightimagery.com.yml']
    for path, _, files in os.walk(args.data):
        for fname in files:
            if not fname.endswith('.yml'):
                continue
            filepath = os.path.join(path, fname)
            (domain, _) = os.path.splitext(fname)

            parse_config(filepath, domain, args)

if __name__ == '__main__':
    main()
