from __future__ import annotations

import rackspace.Api

import base64
import datetime
import hashlib
import http.client
import json
import logging
import requests
import time
import yaml

# a = Api('eGbq9/2hcZsRlr1JV1Pi', 'QHOvchm/40czXhJ1OxfxK7jDHr3t', time_stamp=20010317143725, user_agent='Rackspace Management Interface')
API_URL = 'https://api.emailsrvr.com'
RATE_LIMIT = {}

def rate_limit(rate: int =90, _id: str =None):
    def outer_wrapper(func, _id=_id):
        if _id is None:
            _id = func.__name__

        def inner_wrapper(*pargs, **kwargs):
            interval = 60 / rate
            now = time.time()
            diff = now - RATE_LIMIT[_id] if _id in RATE_LIMIT else now

            if _id in RATE_LIMIT and diff < interval:
                wait = interval - diff
                time.sleep(wait)

            RATE_LIMIT[_id] = now

            return func(*pargs, **kwargs)
        return inner_wrapper

    return outer_wrapper

class Api(object):
    def __init__(self: Api,
            user_key: str,
            secret_key: str,
            customer_id: int = None,
            api_url: str =API_URL,
            time_stamp: str =None,
            user_agent: str =None,
            domain: str =None,
            *pargs,
            **kwargs
            ) -> None:
        headers = requests.utils.default_headers()

        if customer_id is not None:
            self.customer = customer_id

        if domain is not None:
            self.set_domain(domain)

        if user_agent is None:
            user_agent = headers.get('User-Agent')

        else:
            headers.update({'User-Agent': user_agent})

        headers.update({'Accept': 'application/json'})

        if time_stamp is None:
            time_stamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

        self.headers = headers
        self.time_stamp = time_stamp
        self.user_key = user_key
        self.secret_key = secret_key
        self.user_agent = user_agent
        self.api_url = api_url

        self.token_sha = None
        self.auth_token = None

    @property
    def customer(self: Api) -> str:
        return self.__customer
    @customer.setter
    def customer(self: Api, value: str) -> None:
        self.__customer=value

    @property
    def domain(self: Api) -> str:
        return self.__domain
    @domain.setter
    def domain(self: Api, value: str) -> None:
        self.__domain=value

    def set_domain(self: Api, domain: str) -> None:
        self.__domain = domain

    def genAuth(self: Api, new: bool =False, time_stamp: str =None) -> str:
        if time_stamp is not None:
            self.time_stamp = time_stamp
            self._genTokenSha()

        elif new:
            self.time_stamp = '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
            self._genTokenSha()

        elif self.token_sha is None:
            self._genTokenSha()

        token = f'{self.user_key}:{self.time_stamp}:{self.token_sha}'
        self.headers.update({'X-Api-Signature': token})

        return token
    
    def _genTokenSha(self: Api) -> None:
        base_str = f'{self.user_key}{self.user_agent}{self.time_stamp}{self.secret_key}'
        ### print(base_str)

        sha1 = hashlib.sha1(base_str.encode())
        ### print(sha1.hexdigest())

        b64 = base64.b64encode(sha1.digest())
        ### print(b64.decode())

        self.token_sha = b64.decode()

    @staticmethod
    def _params(*pargs, **kwargs) -> (dict, str):
        args = ''
        params = {}
        for k,v in kwargs.items():
            params.update({k: v})
            sep = '?' if args else '&'
            args = f'{args}{sep}{k}={v}'

        return params, args

    def _headers(self: Api) -> dict:
        self.genAuth()

        return self.headers

    @rate_limit(120)
    def get(self: Api, path: str, *pargs, **kwargs) -> requests.Response:
        URL = self._url(path)

        params, args = self._params(*pargs, **kwargs)

        print(''.join((URL,args)))

        return requests.get( URL, headers=self._headers(), params=params)

    @rate_limit(90, 'send')
    def put(self: Api, *pargs, **kwargs) -> requests.Response:
        return self.__putpost(requests.put, *pargs, **kwargs)

    @rate_limit(90, 'send')
    def post(self: Api, *pargs, **kwargs) -> requests.Response:
        return self.__putpost(requests.post, *pargs, **kwargs)

    def __putpost(self: Api, func: function, path: str, data: dict, *pargs, **kwargs) -> requests.Response:
        URL = self._url(path)

        params, args = self._params(*pargs, **kwargs)
        print(''.join((URL,args)))

        return func(URL, data=data, headers=self._headers(), params=params)

    @rate_limit(90, 'send')
    def delete(self: Api, path: str, data: dict =None, *pargs, **kwargs) -> requests.Response:
        URL = self._url(path)

        params, args = self._params(*pargs, **kwargs)
        print(''.join((URL,args)))

        return requests.delete( URL, headers=self._headers(), params=params)

    def _url(self: Api, path: str) -> str:
        return f'{self.api_url}{path}'

    def _customer_path(self: Api) -> str:
        return f'/v1/customers/{self.customer}'

    def _domain_path(self: Api) -> str:
        return f'{self._customer_path()}/domains/{self.domain}'

    def _accounts_path(self: Accounts) -> str:
        return f'{self._domain_path()}/rs/mailboxes'

    def _account_path(self: Accounts, account: str) -> str:
        return f'{self._accounts_path()}/{account}'

    def _aliases_path(self: Aliases) -> str:
        return f'{self._domain_path()}/rs/aliases'

    def _alias_path(self: Aliases, alias: str) -> str:
        return f'{self._aliases_path()}/{alias}'

    @staticmethod
    def httpclient_logging_unpatch(level: int =logging.DEBUG) -> None:
        logging.disable(level)

        delattr(http.client, 'print')
        http.client.HTTPConnection.debuglevel = 0

    @staticmethod
    def httpclient_logging_patch(level: int =logging.DEBUG) -> None:
        logging.basicConfig(level=level)
        httpclient_logger = logging.getLogger('http.client')

        def httpclient_log(*pargs):
            httpclient_logger.log(level, ' '.join(pargs))
    
        http.client.print = httpclient_log
    
        http.client.HTTPConnection.debuglevel = 1

    @staticmethod
    def _success(response: requests.Response, status_code: int =200) -> bool:
        if response.status_code != status_code:
            if response.text:
                print(json.dumps(response.json(), sort_keys=True, indent=4))
            return False
        return True
