from __future__ import annotations

import rackspace.Api
import requests
from rackspace import Alias

PAGE_SIZE = 50

class RetreiveLimit(Exception):
    pass

class Aliases(object):
    def __init__(self: Aliases, api: rackspace.Api) -> None:
        self.api = api

        # Ensure api is ready to make connections
        self.api.genAuth()

    ### def _aliases_path(self: Aliases) -> str:
    ###     return f'{self.api._domain_path()}/rs/aliases'

    ### def _alias_path(self: Aliases, alias: str) -> str:
    ###     return f'{self.api._aliases_path()}/{alias}'

    def _get_aliases(self: Aliases, *pargs: list, **kwargs: dict) -> requests.Response:
        path = f'{self.api._aliases_path()}/'

        return self.api.get(path, *pargs, **kwargs)

    def get_aliases(self: Aliases, limit=None, *pargs: list, **kwargs: dict) -> dict:
        aliases = {}

        ### size = kwargs['size'] if 'size' in kwargs else PAGE_SIZE
        ### offset = kwargs['offset'] if 'offset' in kwargs else 0
        ### print(f'get_aliases(offset={offset}, size={size})')

        while True:
            response = self._get_aliases(*pargs, **kwargs)
            assert response.status_code == 200 and response.text
            data = response.json()

            try:
                # Loop over each entry
                for idx, alias in enumerate(data['aliases']):

                    # If we specified a limit to retrieve, disable the outer loop and 
                    if isinstance(limit, int) and len(aliases) >= limit:
                        raise RetreiveLimit

                    ### print(f'get_aliases()[{idx + data["offset"]}] => {alias}')

                    # If target is a single address, we have all the info needed
                    if alias['numberOfMembers'] == 1:
                        aliases.update({alias['name']: Alias.Alias(alias, api=self.api)})

                    # If there are more than 1 target, we don't have the addresses
                    # and have to call the singular get_alias method, instead
                    elif alias['numberOfMembers'] > 1:
                        alias = self.get_alias(alias['name'], *pargs, **kwargs)
                        aliases.update({alias.name: alias})

            # If we hit the limit, break the main loop
            except RetreiveLimit:
                break

            # If this is the last page of info, break the main loop
            if data['offset'] + data['size'] > data['total']:
                break

            # Not the last page, set data to get next page
            # and loop again
            kwargs['size'] = data['size']
            kwargs['offset'] = data['offset'] + data['size']

        return aliases

    def _get_alias(self: Aliases, alias: str, *pargs: list, **kwargs: dict) -> requests.Response:
        path = f'{self.api._alias_path(alias)}'

        return self.api.get(path, *pargs, **kwargs)

    def get_alias(self: Aliases, alias: str, *pargs: list, **kwargs: dict) -> dict:
        response = self._get_alias(alias, *pargs, **kwargs)
        assert response.status_code == 200
        data = response.json()

        ### print(f'get_alias({alias}) => {data}')
        return Alias.Alias(data=data, api=self.api)

    ### def add_alias(self: Aliases, alias: str, targets: list, _set: bool =False, *pargs: list, **kwargs: dict) -> requests.Response:
    ###     path = f'{self.api._alias_path(alias)}'

    ###     data = { 'aliasEmails': ','.join(targets) }

    ###     func = self.api.put if _set else self.api.post

    ###     return func(path, data, *pargs, **kwargs)

    ### def del_alias(self: Aliases, alias: str, *pargs: list, **kwargs: dict) -> requests.Response:
    ###     path = f'{self.api._alias_path(alias)}'

    ###     return self.api.delete(path, *pargs, **kwargs)

    ### def update_alias(self: Aliases, alias: str, address: str, add: bool =False, remove: bool =False, *pargs: list, **kwargs: dict) -> requests.Response:
    ###     path = f'{self.api._alias_path(alias)}/{address}'

    ###     if add:
    ###         func = self.api.post
    ###     elif remove:
    ###         func = self.api.delete
    ###     else:
    ###         if not address:
    ###             return self.del_alias(alias, *pargs, **kwargs)

    ###         if isinstance(address, str):
    ###             address = [address]

    ###         return add_alias(alias, address, _set=True, *pargs, **kwargs)

    ###     return func(path, data={}, *pargs, **kwargs)

