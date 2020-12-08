from __future__ import annotations

import requests

from .account import Account
from .api import Api


class RetrieveLimit(Exception):
    pass


class Accounts(object):
    def __init__(self, api: Api) -> None:
        self.api = api

        self.api.gen_auth()

    def get(self, limit=None, *pargs: list, **kwargs: dict) -> dict:
        """API: Get list of accounts

        Get a list of all accounts, instantiating Account objects for them

        Args:
           limit (int, optional): Maximum number of accounts to return
           size (int, optional): Number of entries per page to return, default 50
           offset (int, optional): Page number to get `size` entries

        Returns:
           dict: {`name`: Account()} list of accounts

        Raises:
           None
        """
        accounts = {}

        path = f'{self.api._accounts_path()}/'

        while True:
            response = self.api.get(path, *pargs, **kwargs)
            assert response.status_code == 200 and response.text
            data = response.json()

            try:
                for idx, account_meta in enumerate(data['rsMailboxes']):
                    if isinstance(limit, int) and len(accounts) >= limit:
                        raise RetrieveLimit

                    ### print(f'get_accounts()[{idx + data["offset"]}] => {account_meta}')

                    account = Account(account_meta['name'], api=self.api).get()
                    #account = self.get_account(account_meta['name'])
                    accounts.update({account.name: account})

            except RetrieveLimit:
                break

            # If this is the last page of info, break the main loop
            if data['offset'] + data['size'] > data['total']:
                break

            # Not the last page, set data to get next page
            # and loop again
            kwargs['size'] = data['size']
            kwargs['offset'] = data['offset'] + data['size']

        return accounts
