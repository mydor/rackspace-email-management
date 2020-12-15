from __future__ import annotations
from typing import Optional, Tuple, Callable

import base64
import datetime
import hashlib
import http.client
import json
import logging
import requests
import time
import yaml

API_URL: str = 'https://api.emailsrvr.com'
RATE_LIMIT_WAIT = 5

# Note: Rackspace returns "403 Forbidden" for rate limit responses,
# instead of the correct "429 Too Many Requests".
# As they publish what the limits are, I just wrap the request
# calls with the rate_limit decorator to pre-throttle the calls
# and prevent the 403.
def rate_limit(rate: int =90, _id: str =None):
    def outer_wrapper(func, _id=_id):
        if _id is None:
            _id = func.__name__

        def inner_wrapper(*pargs, **kwargs):
            while True:
                response = func(*pargs, **kwargs)

                # Catch rate limit and repeat request
                if response.status_code == 403 and response.text:
                    msg = response.json()
                    if 'unauthorizedFault' in msg and msg['unauthorizedFault'].get('message', '') == 'Exceeded request limits':
                        print(f'- ERROR: Rate Limit exceeded, sleeping {RATE_LIMIT_WAIT}, then retry')
                        time.sleep(RATE_LIMIT_WAIT)
                        continue

                # Not rate limited, break the loop and return
                break

            return response
        return inner_wrapper
    return outer_wrapper


class Api(object):
    """Api object with all knowledge for API calls to Rackspace

    Attributes:
       customer (int): Rackspace customer #
       domain (str): Rackspace domain
    """
    def __init__(self,
            user_key: str,
            secret_key: str,
            customer_id: str = None,
            api_url: str = API_URL,
            time_stamp: str = None,
            user_agent: str = None,
            domain: str = None,
            *pargs,
            **kwargs
            ) -> None:
        f"""Create an Api object

        Instantiate an object of Api

        Args:
           user_key (str): Rackspace API User Key
           secret_key (str): Rackspace API Secret Key
           customer_id (int, optional): Rackspace Customer #
           domain (str, optional): Rackspace domain
           api_url (str, optional): Rackspace API URL defaults {API_URL}
           time_stamp (str, optional): Time Stamp used for API Token, defaults to `datetime.now`
           user_agent (str, optional): Web User Agent to report for API calls, defaults to `requests` standard UA

        Returns:
           None

        Raises:
           None
    
        Example:
           api = Api('eGbq9/2hcZsRlr1JV1Pi', 'QHOvchm/40czXhJ1OxfxK7jDHr3t', time_stamp=20010317143725, user_agent='Rackspace Management Interface')
        """
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

        self.headers: dict = headers
        self.time_stamp: str = time_stamp
        self.user_key: str = user_key
        self.secret_key: str = secret_key
        self.user_agent: str = user_agent
        self.api_url: str = api_url

        self.token_sha: Optional[str] = None
        self.auth_token: Optional[str] = None

    @property
    def customer(self) -> str:
        return self.__customer
    @customer.setter
    def customer(self, value: str) -> None:
        self.__customer=value

    @property
    def domain(self) -> str:
        return self.__domain
    @domain.setter
    def domain(self, value: str) -> None:
        self.__domain=value

    def set_domain(self, domain: str) -> None:
        """Sets API domain

        Args:
           domain (str): Domain to make requests for
        
        Returns:
           None

        Raises:
           None
        """
        self.__domain = domain

    def gen_auth(self, new: bool =False, time_stamp: str =None) -> str:
        """Generate auth token for API calls

        Returns cached auth token, or generate a new token

        Args:
           new (bool): True to force a new auth token
           time_stamp (str, optional): Time stamp to use for auth token ('YYYYmmddHHMMSS' format)

        Returns:
           str: Authentication token

        Raises:
           None
        """
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
    
    def _genTokenSha(self) -> str:
        """Generate the Auth Token SHA hash

        Args:

        Returns:
           str: Auth Token SHA hash

        Raises:
           None
        """
        base_str = f'{self.user_key}{self.user_agent}{self.time_stamp}{self.secret_key}'

        sha1 = hashlib.sha1(base_str.encode())

        b64 = base64.b64encode(sha1.digest())

        self.token_sha = b64.decode()

        return self.token_sha

    @staticmethod
    def _params(*pargs, **kwargs) -> Tuple[dict, str]:
        """Create a shallow copy of kwargs

        Creates a shallow copy of kwargs and data for debug

        Args:

        Returns:
           dict: shallow copy of `**kwargs`
           str: URL args string (for debug output)
        
        Raises:
           None
        """
        args = ''
        params = {}
        for k,v in kwargs.items():
            params.update({k: v})
            sep = '?' if args else '&'
            args = f'{args}{sep}{k}={v}'

        return params, args

    def _headers(self) -> dict:
        """Get the API headers

        Returns the API HTTP headers for a call

        Args:

        Returns:
           dict: HTTP Headers

        Raises:
           None
        """
        self.gen_auth()

        return self.headers

    @rate_limit(120)
    def get(self, *pargs, **kwargs) -> requests.Response:
        """API: `get` data from the rackspace API

        Requests data from the Rackspace API, ensuring we don't exceed our `get` rate limit

        Args:
           path (str): API path to request

        Returns:
           requests.Response: Response for the GET call

        Raises:
           None
        """
        return self.__send(requests.get, *pargs, **kwargs)

    @rate_limit(90, 'send')
    def put(self, *pargs, **kwargs) -> requests.Response:
        """API: Update `put` resouce in Rackspace API

        Updates the data of a resouce in the Rackspace API, ensuring we don't exceed
        our `send` rate limit

        NOTES:
           See `__send()`

        Args:

        Returns:
           requests.Response: Response for the PUT call

        Raises:
           None
        """
        return self.__send(requests.put, *pargs, **kwargs)

    @rate_limit(90, 'send')
    def post(self, *pargs, **kwargs) -> requests.Response:
        """API: Create `post` a resouce in Rackspace API

        Creates a new resouce in the Rackspace API, ensuring we don't exceed
        our `send` rate limit

        NOTES:
           See `__send()`

        Args:

        Returns:
           requests.Response: Response for the POST call

        Raises:
           None
        """
        return self.__send(requests.post, *pargs, **kwargs)

    def __send(self, func: Callable, path: str, data: dict =None, *pargs, **kwargs) -> requests.Response:
        """API: Private method for `get`, `put`, `post`, and `delete`

        Private method to do the work of `get`, `put`, `post`, and `delete`, as they are basically identical
        in how they are called

        Args:
           func (function): `request.put` or `request.post` function
           path (str): API path for this request
           data (dict) Data to be sent to the API

        Returns:
           requests.Response: Response for the `put`/`post` call

        Raises:
           None
        """
        URL = self._url(path)

        params, args = self._params(*pargs, **kwargs)
        print('{} {}'.format(func.__name__.upper(), ''.join((URL,args))))

        return func(URL, data=data, headers=self._headers(), params=params)

    @rate_limit(90, 'send')
    def delete(self, *pargs, **kwargs) -> requests.Response:
        """API: Delete resource from Rackspace

        Delete the resource from the Rackspace API, ensuring we do not exceed
        our `send` rate limit

        NOTES:
           See `__send()`

        Args:

        Returns:
           requests.Response: Response for the DELETE call

        Raises:
           None
        """
        return self.__send(requests.delete, *pargs, **kwargs)

    def _url(self, path: str) -> str:
        """Construct the full URL for an API call

        The `path` will be appended to the API url

        Args:
           path (str): API path for this request

        Returns:
           str: Full URL for the API call

        Raises:
           None
        """
        return f'{self.api_url}{path}'

    def _customer_path(self, ver: int =1) -> str:
        """Construct the path for customer root path

        Args:
           ver (int, optional): API Version, defaults to 1
        
        Returns:
           str: Customer API path

        Raises:
           None
        """
        return f'/v{ver}/customers/{self.customer}'

    def _domain_path(self, *pargs, **kwargs) -> str:
        """Construct the path for the domain root path

        NOTES:
           See `_customer_path()`

        Args:

        Returns:
           str: Domain API path

        Raises:
           None
        """
        root = self._customer_path(*pargs, **kwargs)
        return f'{root}/domains/{self.domain}'

    def _accounts_path(self, *pargs, **kwargs) -> str:
        """Construct the path for the accounts root path

        NOTES:
           See `_domain_path()`

        Args:

        Returns:
           str: Accounts API path

        Raises:
           None
        """
        root = self._domain_path(*pargs, **kwargs)
        return f'{root}/rs/mailboxes'

    def _account_path(self, account: str, *pargs, **kwargs) -> str:
        """Construct the path for an account root path

        NOTES:
           See `_accounts_path()`

        Args:
           account (str): Account name for the request

        Returns:
           str: Account API path

        Raises:
           None
        """
        root = self._accounts_path(*pargs, **kwargs)
        return f'{root}/{account}'

    def _aliases_path(self, *pargs, **kwargs) -> str:
        """Construct the path for aliases root path

        NOTE:
           See `_domain_path()`

        Args:

        Returns:
           str: Aliases API path

        Raises:
           None
        """
        root = self._domain_path(*pargs, **kwargs)
        return f'{root}/rs/aliases'

    def _alias_path(self, alias: str, *pargs, **kwargs) -> str:
        """Construct the path for an alias root path

        NOTE:
           See `_aliases_path()`

        Args:
           alias (str): Name of alias for call

        Returns:
           str: Alias API path

        Raises:
           None
        """
        root = self._aliases_path(*pargs, **kwargs)
        return f'{root}/{alias}'

    @staticmethod
    def httpclient_logging_unpatch(level: int =logging.DEBUG) -> None:
        """Patch http.client to disable logging

        Ugly patch to http.client to disable logging queries and headers/data

        Args:
           level (int, optional): Logging level, default to `logging.DEBUG`

        Returns:
           None

        Raises:
           None
        """
        logging.disable(level)

        delattr(http.client, 'print') # type: ignore
        http.client.HTTPConnection.debuglevel = 0 # type: ignore

    @staticmethod
    def httpclient_logging_patch(level: int =logging.DEBUG) -> None:
        """Patch http.client to log queries

        Ugly patch to http.client to force it to log queries and headers/data

        Args:
           level (int, optional): Logging level, default to `logging.DEBUG`

        Returns:
           None

        Raises:
           None
        """
        logging.basicConfig(level=level)
        httpclient_logger = logging.getLogger('http.client')

        def httpclient_log(*pargs):
            httpclient_logger.log(level, ' '.join(pargs))
    
        http.client.print = httpclient_log # type: ignore
    
        http.client.HTTPConnection.debuglevel = 1 # type: ignore

    @staticmethod
    def _success(response: requests.Response, status_code: int =200) -> bool:
        """Check response for "success"

        Checks the response object for "success", normally status_code 200
        Dumps the message on "failure"

        Args:
           response (requests.Response): response object to test
           status_code (int, optional): Status code considered "success", default 200

        Returns:
           bool: True if response status code matches expected code

        Raises:
           None
        """
        if response.status_code != status_code:
            if response.text:
                print(json.dumps(response.json(), sort_keys=True, indent=4))
            return False
        return True
