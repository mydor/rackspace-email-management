from __future__ import annotations

from rackspace import Account
import rackspace.Api
import requests
# a = Api('eGbq9/2hcZsRlr1JV1Pi', 'QHOvchm/40czXhJ1OxfxK7jDHr3t', time_stamp=20010317143725, user_agent='Rackspace Management Interface')

class RetreiveLimit(Exception):
    pass

class Accounts(object):
    def __init__(self: Accounts, api: rackspace.Api) -> None:
        self.api = api

        self.api.genAuth()

    ### def _accounts_path(self: Accounts) -> str:
    ###     return f'{self.api._domain_path()}/rs/mailboxes'

    ### def _account_path(self: Accounts, account: str) -> str:
    ###     return f'{self._accounts_path()}/{account}'

    def _get_accounts(self: Accounts, *pargs: list, **kwargs: dict) -> requests.Response:
        path = f'{self.api._accounts_path()}/'

        return self.api.get(path, *pargs, **kwargs)

    def get_accounts(self: Accounts, limit=None, *pargs: list, **kwargs: dict) -> dict:
        accounts = {}

        while True:
            response = self._get_accounts(*pargs, **kwargs)
            assert response.status_code == 200 and response.text
            data = response.json()

            try:
                for idx, account_meta in enumerate(data['rsMailboxes']):
                    if isinstance(limit, int) and len(accounts) >= limit:
                        raise RetreiveLimit

                    ### print(f'get_accounts()[{idx + data["offset"]}] => {account_meta}')

                    account = self.get_account(account_meta['name'])
                    accounts.update({account_meta['name']: account})

            except RetreiveLimit:
                break

            # If this is the last page of info, break the main loop
            if data['offset'] + data['size'] > data['total']:
                break

            # Not the last page, set data to get next page
            # and loop again
            kwargs['size'] = data['size']
            kwargs['offset'] = data['offset'] + data['size']

        return accounts

    def _get_account(self: Accounts, account: str, *pargs: list, **kwargs: dict) -> requests.Response:
        path = f'{self.api._account_path(account)}/'

        return self.api.get(path, *pargs, **kwargs)

    def get_account(self: Accounts, account: str, *pargs: list, **kwargs: dict) -> Account:
        response = self._get_account(account, *pargs, **kwargs)
        assert response.status_code == 200 and response.text
        data = response.json()

        return Account.Account(data, api=self.api)

    def add_account(self: Accounts, account: str, data: dict, *pargs: list, **kwargs: dict) -> requests.Response:
        path = f'{self.api._account_path(account)}'

        return self.api.post(path, data, *pargs, **kwargs)
    
    def del_account(self: Accounts, account: str, *pargs: list, **kwargs: dict) -> requests.Response:
        path = f'{self.api._account_path(account)}'

        return self.api.delete(path, *pargs, **kwargs)

    def rename_account(self: Accounts, oldname: str, newname: str, *pargs: list, **kwargs: dict) -> requests.Response:
        path = f'{self.api._account_path(oldname)}'

        return self.api.put(path, data={'name': newname}, *pargs, **kwargs)

    def update_account(self: Accounts, account: str, data: dict, *pargs: list, **kwargs: dict) -> requests.Response:
        path = f'{self.api._account_path(account)}'

        return self.api.put(path, data=data, *pargs, **kwargs)


