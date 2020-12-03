#!/bin/env python3

from mail import Domain
from mail import Account

import requests
import http.client
import logging
import yaml
import hashlib
import base64
import datetime
import json

CONFIG = None
HEADERS = requests.utils.default_headers()

def authTokenSha(user_agent=None, user_key=None, secret_key=None, time_stamp=None):
    if user_agent is None:
        if CONFIG is not None and 'user_agent' in CONFIG:
            user_agent = CONFIG['user_agent']
        else:
            user_agent = HEADERS['User-Agent']

    if CONFIG is not None and user_key is None:
        user_key = CONFIG['user_key']

    if CONFIG is not None and secret_key is None:
        secret_key = CONFIG['secret_key']

    if time_stamp is None:
        time_stamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

    base_str = f'{user_key}{user_agent}{time_stamp}{secret_key}'
    ### print(base_str)

    sha1 = hashlib.sha1(base_str.encode())
    ### print(sha1.hexdigest())

    b64 = base64.b64encode(sha1.digest())
    ### print(b64.decode())
    return b64.decode()

def authToken(user_key=None, time_stamp=None, sha1_hash=None, *pargs, **kwargs):
    if time_stamp is None:
        time_stamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

    if CONFIG is not None and user_key is None:
        user_key = CONFIG['user_key']

    if sha1_hash is None:
        sha1_hash = authTokenSha(user_key=user_key, time_stamp=time_stamp, *pargs, **kwargs)

    token = f'{user_key}:{time_stamp}:{sha1_hash}'
    ### print(token)
    return token

def loadConfig(name=None):
    if name is None:
        name = 'cfg.yml'

    with open(name, 'r') as fh:
        raw = fh.read()

    config = yaml.safe_load(raw)

    return config

def _url(path):
    return CONFIG['api_url'] + path

def get_aliases(domain, *pargs, **kwargs):
    path = f'/v1/customers/{CONFIG["customer_id"]}/domains/{domain}/rs/aliases/'

    return _get(path, *pargs, **kwargs)

def get_alias(domain, alias, *pargs, **kwargs):
    path = f'/v1/customers/{CONFIG["customer_id"]}/domains/{domain}/rs/aliases/{alias}'

    return _get(path, *pargs, **kwargs)

def add_alias(domain, alias, targets, _set=False, *pargs, **kwargs):
    path = f'/v1/customers/{CONFIG["customer_id"]}/domains/{domain}/rs/aliases/{alias}'

    data = { 'aliasEmails': ','.join(targets) }

    func = _put if _set else _post

    return func(path, data)

def update_alias(domain, alias, address, add=False, remove=False, *pargs, **kwargs):
    path = f'/v1/customers/{CONFIG["customer_id"]}/domains/{domain}/rs/aliases/{alias}/{address}'

    if add:
        func = _post
    elif remove:
        func = _delete
    else:
        if not address:
            return del_alias(domain, alias, *pargs, **kwargs)

        if isinstance(address, str):
            address = [address]

        return add_alias(domain, alias, address, _set=True, *pargs, **kwargs)

    return func(path, data={}, *pargs, **kwargs)

def del_alias(domain, alias, *pargs, **kwargs):
    path = f'/v1/customers/{CONFIG["customer_id"]}/domains/{domain}/rs/aliases/{alias}'

    return _delete(path, *pargs, **kwargs)

def get_accounts(domain, *pargs, **kwargs):
    path = f'/v1/customers/{CONFIG["customer_id"]}/domains/{domain}/rs/mailboxes/'

    return _get(path, *pargs, **kwargs)

def get_account(domain, name, *pargs, **kwargs):
    path = f'/v1/customers/{CONFIG["customer_id"]}/domains/{domain}/rs/mailboxes/{name}'
    return _get(path, *pargs, **kwargs)

def _headers(auth=None):
    headers = HEADERS.copy()
    if 'X-Api-Signature' not in headers:
        if auth is None:
            auth = authToken()
        headers.update({'X-Api-Signature': auth})

    ### print(json.dumps(dict(headers), sort_keys=True, indent=4))

    return dict(headers)

def _params(*pargs, **kwargs):

    args = ''
    params = {}
    for k,v in kwargs.items():
        params.update({k: v})
        sep = '?' if args else '&'
        args = f'{args}{sep}{k}={v}'

    return params, args

def _delete(path, auth=None, *pargs, **kwargs):
    URL = _url(path)

    params, args = _params(*pargs, **kwargs)

    print(''.join((URL,args)))

    headers = _headers(auth=auth)

    return requests.delete(URL, headers=headers, params=params)

def _put(path, data, auth=None, *pargs, **kwargs):
    URL = _url(path)

    params, args = _params(*pargs, **kwargs)
    print(''.join((URL,args)))

    headers = _headers(auth=auth)

    return requests.put(URL, data=data, headers=headers, params=params)

def _post(path, data, auth=None, *pargs, **kwargs):
    URL = _url(path)

    params, args = _params(*pargs, **kwargs)

    print(''.join((URL,args)))

    headers = _headers(auth=auth)

    return requests.post(URL, data=data, headers=headers, params=params)

def _get(path, auth=None, getAll=False, *pargs, **kwargs):
    URL = _url(path)

    params, args = _params(*pargs, **kwargs)

    print(''.join((URL,args)))

    headers = _headers(auth=auth)

    return requests.get( URL, headers=headers, params=params)

def httpclient_logging_patch(level=logging.DEBUG):
    def httpclient_log(*pargs):
        httpclient_logger.log(level, ' '.join(pargs))

    http.client.print = httpclient_log

    http.client.HTTPConnection.debuglevel = 1

def setHTTPHeaders(auth=None):
    HEADERS.update({'Accept': 'application/json'})

    if auth:
        HEADERS.update({'X-Api-Signature': auth})

    if CONFIG is not None and 'user_agent' in CONFIG:
        HEADERS.update({'User-Agent': CONFIG['user_agent']})

def processDomain(domain):
    with open(f'{domain}.yml', 'r') as fh:
        raw = fh.read()

    domain_data = yaml.safe_load(raw)
    _domain = Domain(domain)

    if domain_data is not None:
        for account, account_data in domain_data.items():
            obj = Account(domain, account, account_data)
            _domain.addAccount(obj)

            if 'aliases' not in account_data:
                continue 

            for alias in account_data['aliases']:
                _domain.addAlias(alias, account)

    print(_domain)

if __name__ == '__main__':
    CONFIG = loadConfig()

    #logging.basicConfig(level=logging.DEBUG)
    #httpclient_logger = logging.getLogger('http.client')
    #httpclient_logging_patch()

    auth_token = authToken()
    setHTTPHeaders(auth=auth_token)

    for domain in CONFIG['domains']:
        processDomain(domain)

    #response = get_aliases('moonlightimagery.com')
    #assert response.status_code == 200
    #print(json.dumps(response.json(), sort_keys=True, indent=4))
    #response = get_aliases('arch-mage.com')
    #assert response.status_code == 200
    #print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_accounts('moonlightimagery.com')
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_accounts('arch-mage.com', size=1)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_accounts('arch-mage.com', size=1,offset=1)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_account('arch-mage.com', 'archmage-tn')
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_aliases('arch-mage.com', size=5)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_alias('arch-mage.com', 'avantgo', size=5)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = del_alias('arch-mage.com', 'testremove')
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### ### print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = add_alias('arch-mage.com', 'testremove', targets=['archmage-tn@arch-mage.com'])
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_alias('arch-mage.com', 'testremove', size=5)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = update_alias('arch-mage.com', 'testremove', 'junk@arch-mage.com', add=True)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_alias('arch-mage.com', 'testremove', size=5)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = update_alias('arch-mage.com', 'testremove', 'archmage-tn@arch-mage.com', remove=True)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_alias('arch-mage.com', 'testremove', size=5)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = update_alias('arch-mage.com', 'testremove', ['archmage-tn@arch-mage.com'])
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_alias('arch-mage.com', 'testremove', size=5)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = update_alias('arch-mage.com', 'testremove', None)
    ### print(response.status_code)
    ### assert response.status_code == 200
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))

    ### response = get_alias('arch-mage.com', 'testremove', size=5)
    ### print(response.status_code)
    ### assert response.status_code == 404
    ### if response.text:
    ###     print(json.dumps(response.json(), sort_keys=True, indent=4))
