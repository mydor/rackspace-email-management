from __future__ import annotations

import requests

from .alias import Alias
from .api import Api

PAGE_SIZE = 50


class RetrieveLimit(Exception):
    pass


class Aliases(object):
    def __init__(self, api: Api) -> None:
        self.api = api

        # Ensure api is ready to make connections
        self.api.gen_auth()

    def _get_aliases(self, *pargs: list, **kwargs: dict) -> requests.Response:
        """API: Get page of aliases

        Get a page of aliases from the rackspace API

        Args:

        Returns:
           requests.Response: Response of the request

        Raises:
           None
        """
        path = f'{self.api._aliases_path()}/'

        return self.api.get(path, *pargs, **kwargs)

    def get_aliases(self, limit=None, *pargs: list, **kwargs: dict) -> dict:
        """API: Get list of aliases

        Get a list of all aliases, instantiating Alias objects for them

        Args:
           limit (int, optional): Maximum number of aliases to return
           size (int, optional): Number of entries per page to retieve at a time, default 50
           offset (int, optional): Page number to get `size` entries

        Returns:
           dict: {`name`: Alias()} list of aliases

        Raises:
           None
        """
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
                        raise RetrieveLimit

                    ### print(f'get_aliases()[{idx + data["offset"]}] => {alias}')

                    alias_obj = Alias(alias['name'], api=self.api)
                    # If target is a single address, we have all the info needed
                    if alias['numberOfMembers'] == 1:
                        alias_obj.load(data=alias)

                    # If there are more than 1 target, we don't have the addresses
                    # and have to call the api to load the members instead
                    elif alias['numberOfMembers'] > 1:
                        alias_obj = alias_obj.get()

                    # Save the alias to our dictionary
                    aliases.update({alias_obj.name: alias_obj})

            # If we hit the limit, break the main loop
            except RetrieveLimit:
                break

            # If this is the last page of info, break the main loop
            if data['offset'] + data['size'] > data['total']:
                break

            # Not the last page, set data to get next page
            # and loop again
            kwargs['size'] = data['size']
            kwargs['offset'] = data['offset'] + data['size']

        return aliases

