from __future__ import annotations

import json

DEBUG = True


class DuplicateLoadError(Exception):
    pass


class Alias(object):
    """Alias object with all knowledge for a single alias

    Attributes:
       name (str): Name of alias, without domain
       addresses (:list:`str`): List of email targets for alias
    """
    def __str__(self) -> None:
        return f'''Alias({{name: "{self.name}", addresses: ["{'", "'.join(self.addresses)}"]}})'''

    def __repr__(self) -> None:
        return self.__str__()

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
                self.addresses = address
            else:
                self.addresses = [address]

            self.loaded = True

            return

        if data is None:
            return

        if all(key in data for key in ('numberOfMembers', 'singleMemberName')) and data['numberOfMembers'] == 1:
            self.addresses = [ data['singleMemberName'] ]

        elif all(key in data for key in ('emailAddressList',)) and 'emailAddress' in data['emailAddressList']:
            self.addresses = data['emailAddressList']['emailAddress']

        else:
            raise

        self.loaded = True

    def __init__(self, name: str, api: Api =None, *pargs, **kwargs) -> None:
        self.name = name
        self.addresses = []
        self.loaded = False

        if api is not None:
            self.api = api

        self.__load(*pargs, **kwargs)

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
        if address not in self.addresses:
            self.addresses.append(address)

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
        diff = {'add': [], 'del': [], 'changes': 0}

        for src, dst, key in ((self, other_alias, 'add'), (other_alias, self, 'del')):
            for address in src.addresses:
                if address not in dst.addresses and address not in diff[key]:
                    diff[key].append(address)
                    diff['changes'] += 1

        return diff

    def get(self, *pargs, **kwargs) -> Alias:
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
            return None

        return Alias(self.name, api=self.api, data=response.json())

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

        data = {'aliasEmails': ','.join(self.addresses)}

        if DEBUG:
            print(f"\n{path}\n   ALIAS ADD: {{'{self.name}' => {self.addresses}}}")
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

        data = {'aliasEmails': ','.join(self.addresses)}

        if DEBUG:
            print(f"\n{path}\n   ALIAS REPLACE: {{'{self.name}' => {self.addresses}}}")
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

        if DEBUG:
            print(f"\n{path}\n   ALIAS REMOVE: '{self.name}'")
        else:
            response = self.api.delete(path, *pargs, **kwargs)
            return self.api._success(response)

    def update(self, address: str, add: bool =False, remove: bool = False, *pargs: list, **kwargs: dict) -> bool:
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

        path = f'{self.api._alias_path(self.name)}/{address}'

        if add:
            func = self.api.post
            xxx = f'add: {address}'

        elif remove:
            func = self.api.delete
            xxx = 'remove: {address}'

        if DEBUG:
            print(f"\n{path}\n   ALIAS UPDATE: {self.name} => {xxx}")
        else:
            response = func(path, data={}, *pargs, **kwargs)
            return self.api._success(response)
