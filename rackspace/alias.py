from __future__ import annotations

import json

from typing import List, Optional

from .api import Api

DEBUG: bool = False
PAGE_SIZE: int = 50

#
# NOTE: The list of email aliases varies by row, depending on if
# the alias has a single destination, or multiple.
# A single destination results in the row having all the information needed
# to construct an Alias() object.
# Multiple destinations requires another GET, for that alias, to retrieve
# the destination addresses needed to construct an Alias() object

class DuplicateLoadError(Exception):
    pass


class RetrieveLimit(Exception):
    pass


class Alias(object):
    """Alias object with all knowledge for a single alias

    Attributes:
       name (str): Name of alias, without domain
       data (:list:`str`): List of email targets for alias
    """
    def __init__(self,
                 name: str,
                 api: Api =None,
                 debug: bool =DEBUG,
                 response: Api.requests.Response =None,
                 *pargs, **kwargs) -> None:
        self.name: str = name.split('@')[0]
        self.data: List[str] = []
        self.loaded: bool = False
        self.debug: bool = debug
        self.response: Api.requests.Response = response

        if api is not None:
            self.api = api

        self.__load(*pargs, **kwargs)

    def __str__(self) -> str:
        return f'''Alias({{name: "{self.name}", data: ["{'", "'.join(self.data)}"]}})'''

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def success(self):
        try:
            return self.api._success(self.response, output=False)
        except:
            return False

    @property
    def canRecover(self):
        return False


    def save(self):
        print(json.dumps(self.data))

    def load(self, data: dict =None) -> None:
        """Load data into Alias object

        Loads data, specified in the 'data' argument, into the Alias object

        Args:
           data (dict): Alias data to be loaded into Alias object,
                        usually from the Rackspace API

        Returns:
           None

        Raises:
           DuplicateLoadError: If Alias object already has data loaded
        """
        self.__load(data=data)

    def __load(self, data: dict = None, name: str =None, address: str = None) -> None:
        """Private data load method

        Private method to load data into Alias object.  Tries to determine if it
        is being loaded by code, or by data from the API, and acts accordingly

        Args:
           data (dict):           Alias data to be loaded into Alias object,
                                  usually from the Rackspace API
           name (str):            Name of the alias
           address (str or list): Address(es) the alias points to

        Returns:
           None

        Raises:
           DuplicateLoadError: If Alias object already has data loaded
        """
        if self.loaded:
            raise DuplicateLoadError("Attempt to load data into already initialized Alias")

        if address is not None:
            if isinstance(address, list):
                self.data = address
            else:
                self.data = [address]

            self.loaded = True

            return

        if data is None:
            return

        if all(key in data for key in ('numberOfMembers', 'singleMemberName')) and data['numberOfMembers'] == 1:
            self.data = [ data['singleMemberName'] ]

        elif all(key in data for key in ('emailAddressList',)) and 'emailAddress' in data['emailAddressList']:
            self.data = data['emailAddressList']['emailAddress']

        elif isinstance(data, list):
            self.data = data

        else:
            raise Exception(f'Should never be here {data}')

        self.loaded = True

    def add_address(self, address: str) -> None:
        """Add new address to alias

        Adds a new address to self.  Only affects the object, and
        does NOT update Rackspace

        Args:
           address (str): FQDN email address to add to the alias

        Returns:
           None

        Raises:
           None
        """
        if address not in self.data:
            self.data.append(address)

    def diff(self, other_alias: Alias) -> dict:
        """Compares two Alias objects

        Compares this (self) Alias object to another Alias object and
        returns the difference results indicating how many addresses need
        to be added (return['add']), how many to be deleted (return['del'])
        and how many total changes were detected (return['changes'])

        Args:
           other_alias (Alias): Alias object to compare to

        Returns:
           dict: 'add'     -> list of addresses that are not in other_alias
                 'del'     -> list of addresses that are not in self
                 'changes' -> total 'add' plus 'del' addresses that were found

        Raises:
           None
        """
        # Since the only content of an alias is a list of target addresses
        # we need to return what is new, to add
        # and what is old, to remove
        diff: dict = {'add': [], 'del': [], 'old': other_alias.data, 'new': self.data, 'changes': 0}

        for src, dst, key in ((self, other_alias, 'add'), (other_alias, self, 'del')):
            for address in src.data:
                if address not in dst.data and address not in diff[key]:
                    diff[key].append(address)
                    diff['changes'] += 1

        return diff

    def get(self, *pargs, **kwargs) -> Optional[Alias]:
        """API: Get the alias data from rackspace

        Calls the rackspace API to retrieve target
        addresses for alias.

        Args:

        Returns:
           Alias: on success, a NEW Alias object, created from rackspace data
                  else, None

        Raises:
           None
        """
        path = f'{self.api._alias_path(self.name)}'
        response = self.api.get(path, *pargs, **kwargs)

        if not self.api._success(response):
            return Alias(self.name, api=self.api, data=self.data, response=response)

        return Alias(self.name, api=self.api, data=response.json(), response=response)

    def add(self, *pargs: list, **kwargs: dict) -> bool:
        """API: Add rackspace alias with addresses

        Adds the alias to rackspace with addresses from self

        Args:

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._alias_path(self.name)}'

        data = {'aliasEmails': ','.join(self.data)}

        if self.debug:
            print(f"\n{path}\n   ALIAS ADD: {{'{self.name}' => {self.data}}}")
            return True
        else:
            response = self.api.post(path, data, *pargs, **kwargs)
            return self.api._success(response)

    def replace(self, *pargs, **kwargs) -> bool:
        """API: Replace rackspace data with new addresses

        Completely replaces the rackspace alias addresses with
        all addresses in self.  Rackspace will exactly match self
        after call.

        Args:

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._alias_path(self.name)}'

        data = {'aliasEmails': ','.join(self.data)}

        if self.debug:
            print(f"\n{path}\n   ALIAS REPLACE: {{'{self.name}' => {self.data}}}")
            return True
        else:
            response = self.api.put(path, data, *pargs, **kwargs)
            return self.api._success(response)


    def remove(self, *pargs: list, **kwargs: dict) -> bool:
        """API: Remove the alias from rackspace

        Removes the alias from rackspace

        Args:

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._alias_path(self.name)}'

        if self.debug:
            print(f"\n{path}\n   ALIAS REMOVE: '{self.name}'")
            return True
        else:
            response = self.api.delete(path, *pargs, **kwargs)
            return self.api._success(response)

    def update(self, data: dict, *pargs: list, **kwargs: dict) -> bool:
        """API: Update the rackspace alias

        Updates the rackspace alias by adding, or removing, a single address.

        If multiple address changes are needed for the alias, it is recommended to
        use `.replace()` instead to reduce the number of API calls.

        Args:
           address (str): Address to add/remove from alias
           add (bool):    Add address (takes precidence if both 'add' and 'remove' are True)
           remove (bool): Remove address

        Returns:
           bool: True on success

        Raises:
           None
        """

        path = f'{self.api._alias_path(self.name)}'

        api_data = {}
        if data['changes'] > 1:
            func = self.api.put
            debug_data = f"set: {' , '.join(data['new'])}"
            api_data = { f"aliasEmails={','.join(data['new'])}" }
            api_data = { 'aliasEmails': ','.join(data['new']) }

        elif data.get('add'):
            func = self.api.post
            debug_data = f"add: {data['add'][0]}"
            path = f"{path}/{data['add'][0]}"

        elif data.get('del'):
            func = self.api.delete
            debug_data = f"remove: {data['del'][0]}"
            path = f"{path}/{data['del'][0]}"

        else:
            print(f"ERROR: {path}")
            raise Exception('Should not be here')

        if self.debug:
            print(f"\n{path}\n   ALIAS UPDATE: {self.name} => {debug_data}")
            return True

        else:
            response = func(path, data=api_data, *pargs, **kwargs)
            return self.api._success(response)


class Aliases(object):
    def __init__(self, api: Api, debug: bool =DEBUG) -> None:
        self.api = api
        self.debug = debug

        # Ensure api is ready to make connections
        self.api.gen_auth()

    def get(self, limit=None, *pargs: list, **kwargs: dict) -> dict:
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
        aliases: dict = {}

        path = f'{self.api._aliases_path()}/'

        while True:
            response = self.api.get(path, *pargs, **kwargs)
            assert response.status_code == 200 and response.text
            data = response.json()

            try:
                for alias in data['aliases']:

                    # If we specified a limit to retrieve, disable the outer loop and
                    if isinstance(limit, int) and len(aliases) >= limit:
                        raise RetrieveLimit

                    alias_obj = Alias(alias['name'], api=self.api, debug=self.debug)

                    # If target is a single address, we have all the info needed
                    if alias['numberOfMembers'] == 1:
                        alias_obj.load(data=alias)

                    # If there are more than 1 target, we don't have the addresses
                    # and have to call the api to load the members instead
                    elif alias['numberOfMembers'] > 1:
                        alias_obj = alias_obj.get() # type: ignore

                    # Save the alias to our dictionary
                    aliases.update({alias_obj.name.lower(): alias_obj})

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

