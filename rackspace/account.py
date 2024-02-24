"""Handle Rackspace Accounts"""
from __future__ import annotations

__author__ = 'Michael Smith'

from typing import Any, Optional, TypeVar

import json
import requests

from .api import Api

SelfAccount = TypeVar("SelfAccount", bound="Account")
SelfAccounts = TypeVar("SelfAccounts", bound="Accounts")

DEBUG = False

# NOTE: The data returned by the Rackspace account API is
# a multi-level nested dictionary of information.
#
# !!! NOTE: This is NOT a valid structure of resource data
# that can be passed to PUT.
#
# The data from GET must be flattened, with the keys renamed
# and having mutually exclusive attributes removed BEFORE
# being passed to PUT.

class DuplicateLoadError(Exception):
    """Repeated Load Error"""
    pass # pylint: disable=unnecessary-pass


class RetrieveLimit(Exception):
    """Exceeded Retrieval Limit"""
    pass # pylint: disable=unnecessary-pass


class Account():
    """Account object with all knowledge for a single account

    Attributes(cls):
       __DEFAULTS (dict): Attributes that must be present, with
                          their default values
       __FIELDS (dict): Attributes that are supported by Rackspace
                        and their data type (str, bool, int)
       __REQUIRED (list): Attributes that are REQUIRED to add an account
                          to rackspace
       __READ_ONLY (list): Attributes that cannot be set, only read

    Attributes(object):
       name (str): Name of account, without domain
       * (*): See cls.__FIELDS
    """
    __DEFAULTS = {
            'enabled': True,
            'size': 25600,
            'visibleInExchangeGAL': True,
            'visibleInRackspaceEmailCompanyDirectory': True,
            }

    __FIELDS = {
            'businessCity': str,
            'businessCountry': str,
            'businessNumber': str,
            'businessPostalCode': str,
            'businessState': str,
            'businessStreet': str,
            'createdDate': str,
            'currentUsage': int,
            'customID': str,
            'displayName': str,
            'employeeType': str,
            'enabled': bool,
            'enableForwardingAddresses': str,
            'enableVacationMessage': bool,
            'faxNumber': str,
            'firstName': str,
            'generationQualifier': str,
            'homeCity': str,
            'homeCountry': str,
            'homeFaxNumber': str,
            'homeNumber': str,
            'homePostalAddress': str,
            'homePostalCode': str,
            'homeState': str,
            'homeStreet': str,
            'initials': str,
            'lastLogin': str,
            'lastName': str,
            'mobileNumber': str,
            'name': str,
            'notes': str,
            'organizationalStatus': str,
            'organization': str,
            'organizationUnit': str,
            'pagerNumber': str,
            'password': str,
            'personalTitle': str,
            'recoverDeleted': bool,
            'saveForwardedEmail': bool,
            'size': int,
            'title': str,
            'userID': str,
            'vacationMessage': str,
            'visibleInExchangeGAL': bool,
            'visibleInRackspaceEmailCompanyDirectory': bool,

            }

    __READONLY = [
            'currentUsage',
            'createdDate',
            'lastLogin',
            'name',
            ]

    __ADD_REQUIRED = [
            'password',
            'size',
            ]

    def __init__( # pylint: disable=too-many-arguments
            self,
            name: str,
            data: dict =None,
            api: Api =None,
            response: Api.requests.Response =None,
            debug: bool =DEBUG) -> SelfAccount:
        """Create an Account object

        Instantiate an object of Account

        Args:
           name (str): Name of the account (without domain)
           api (Api, optional): Api object to communicate with rackspace
           response (Api.requests.Response, optional): requests Response object
           data (dict, optional): Data to load into Account object

        Returns:
           None

        Raises:
           None
        """
        self.name: str = name
        self.loaded: bool = False
        self.debug: bool = debug
        self.response: Api.requests.Response = response

        # Store a copy of the data set, will be useful for the spam module
        self.data = None

        if api is not None:
            self.api = api

        for key,val in Account.__DEFAULTS.items():
            setattr(self, key, val)

        if data:
            self.load(data)
            self.data = data

    def __str__(self) -> str:
        data = f'name: "{self.name}"'
        for field in Account.__FIELDS:
            if field == 'name':
                continue

            value = getattr(self, field, None)
            if value is None or value == '':
                continue

            data = f'{data}, {field}: "{value}"'
        data = f'Account({{{data}}})'
        return data

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def success(self) -> bool:
        """Check if API call returned successfully"""
        return self.api._success(self.response, output=False) # pylint: disable=protected-access

    @property
    def canRecover(self) -> bool: # pylint: disable=invalid-name
        """Check if API call can be recovered"""
        try:
            data = self.response.json()
        except requests.exceptions.JSONDecodeError:
            return False

        return data is not None and data.get('itemNotFoundFault', {})\
            .get('additionalData', {})\
            .get('isRecoverable', False)

    def load( # pylint: disable=too-many-branches
            self,
            data: dict,
            _sub=False) -> None:
        """Load data into Account object

        Loads data into the account object.  This is either from
        a flat dict from the configuration, or a tiered dict from rackspace.
        This will recurse to flatten the rackspace data.

        Note:
           Rackspace data is returned tiered, but must be flat to store
           back to rackspace.  Very poor API interface design

        Args:
           data (dict): Data to load into the object as arguments

        Returns:
           None

        Raises:
           DuplicateLoadError: If Account object already has data loaded
        """
        if self.loaded:
            raise DuplicateLoadError('Attempt to load data into already initialized Account')

        fields = Account.__FIELDS
        ignore = [ 'aliases', 'spam' ]

        for key,val in data.items():
            if key in ignore:
                continue

            if key == 'contactInfo':
                self.load(val, _sub=True)
                continue

            if key == 'emailForwardingAddressList':
                key = 'enableForwardingAddresses'
                val = ','.join(val)

            if key not in fields:
                print(f'Unknown field {key} found')
                continue

            if val is None and fields[key] is str:
                val = ""

            if not isinstance(val, fields[key]):
                if fields[key] is int:
                    val = fields[key](val) # turn string to int

                else:
                    raise TypeError(
                        f'{key} is type {type(val)}, instead of type {fields[key]}')

            # Rackspace likes to sometimes turn empty strings to a single space
            if isinstance(val, str) and val == ' ':
                val = ''

            tmp_val = fields[key](val)
            setattr(self, key, tmp_val)

        if getattr(self, 'displayName', '') == '':
            fname = getattr(self, 'firstName', '')
            lname = getattr(self, 'lastName', '')
            if fname or lname:
                setattr(self, 'displayName', ' '.join((fname, lname)).strip())

        # Only the parent call is allowed to set the loaded flag
        if _sub is False:
            self.loaded=True

    def diff(
            self,
            other_account: Account) -> dict:
        """Compares two Account objects

        Compares this (self) Account object to another Account object
        and returns the difference results, indicating what fields
        need to be updated to make rackspace match our Account

        Args:
           other_account (Account): Account object to compare to

        Returns:
           dict: Fields and their values to be updated

        Raises:
           None
        """
        # Accounts all contain the exact same keys that each only have
        # a single value, no lists or dicts
        # Thus, we are only concerned with what needs to be changed,
        # don't have to worry about what to remove as with Alias objects
        fields = Account.__FIELDS
        readonly = Account.__READONLY
        ignore = ['password', 'recoverDeleted', 'name', 'spam']

        diff = {}
        for field, ftype in fields.items():
            if field in readonly or field in ignore:
                continue

            default: Optional[str | int | bool] = None
            if ftype is str:
                default = ''

            elif ftype is int:
                default = 0

            elif ftype is bool:
                default = False

            new_val = getattr(self, field, default)
            old_val = getattr(other_account, field, default)
            if new_val != old_val:
                diff.update({field: new_val})

        return diff

    def get(
            self,
            *pargs: Optional[list],
            **kwargs: Optional[dict]) -> Optional[Account]:
        """API: Get the account data from rackspace

        Calls the rackspace API to retrieve the account data

        Args:

        Returns:
           Account: on success, a NEW Account object, created from rackspace data
                    else, None

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}' # pylint: disable=protected-access

        response = self.api.get(path, *pargs, **kwargs)

        if not self.api._success(response): # pylint: disable=protected-access
            return Account(self.name, api=self.api, data=self.data, response=response)

        return Account(self.name, api=self.api, data=response.json(), response=response)

    def add( # pylint: disable=keyword-arg-before-vararg
            self,
            data: Optional[dict] =None,
            recover: Optional[bool] =False,
            *pargs: Optional[list],
            **kwargs: Optional[dict]) -> bool:
        """API: Add a new rackspace account

        Adds the account to rackspace

        Args:
           data (dict, optional): For debug purposes, allows creating the account
                                  with arbitrary data

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}' # pylint: disable=protected-access

        fields = Account.__FIELDS
        readonly = Account.__READONLY
        required = Account.__ADD_REQUIRED

        if data is None:
            data = {}
            for field, data_type in fields.items():
                if field in readonly:
                    continue

                default: Any = None
                if data_type is str:
                    default = ''
                elif data_type is int:
                    default = 0
                elif data_type is bool:
                    default = False

                data[field] = getattr(self, field, default)

        if recover:
            data['recoverDeleted'] = True

        is_failed = False
        for req in required:
            if req not in data:
                print(f"Required field {req} missing")
                is_failed = True
        if is_failed:
            raise LookupError('Data missing required fields to add account')

        if self.debug:
            print(f"\n{path}\n   ACCOUNT ADD: '{self.name}'")
            return True

        print(json.dumps(data, indent=4, sort_keys=True))
        response = self.api.post(path, data, *pargs, **kwargs)
        return self.api._success(response) # pylint: disable=protected-access

    def remove(
            self,
            *pargs: Optional[list],
            **kwargs: Optional[dict]) -> bool:
        """API: Remove the account from rackspace

        Removes the account from rackspace

        Args:

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}' # pylint: disable=protected-access

        if self.debug:
            print(f"\n{path}\n   ACCOUNT REMOVE: '{self.name}'")
            return True

        if not input(f"Are you sure you wish to delete {path} (Yes/No)? ").lower() in ('y', 'yes'):
            return True

        response = self.api.delete(path, *pargs, **kwargs)
        return self.api._success(response) # pylint: disable=protected-access

    def rename(
            self,
            newname: str,
            *pargs: Optional[list],
            **kwargs: Optional[dict]) -> bool:
        """API: Rename the account in rackspace

        Renames the account to a new account name

        Args:
           newname (str): New account name (without domain)

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}' # pylint: disable=protected-access

        if self.debug:
            print(f"\n{path}\n   ACCOUNT RENAME: '{self.name}' -> '{newname}'")
            return True

        response = self.api.put(path, data={'name': newname}, *pargs, **kwargs)
        return self.api._success(response) # pylint: disable=protected-access

    def update(
            self,
            data: dict,
            *pargs: Optional[list],
            **kwargs: Optional[dict]) -> bool:
        """API: Update the account in rackspace

        Updates the rackspace account, setting the fields to match `data` or self attributes

        Args:
           data (dict, optional): Data to set on the rackspace account

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}' # pylint: disable=protected-access

        if self.debug:
            print(f"\n{path}\n   ACCOUNT UPDATE: '{self.name}' => {data}")
            return True

        response = self.api.put(path, data=data, *pargs, **kwargs)
        return self.api._success(response) # pylint: disable=protected-access


class Accounts(): # pylint: disable=too-few-public-methods
    """Get all accounts via API"""
    def __init__(
            self,
            api: Api,
            debug: Optional[bool] =DEBUG) -> SelfAccounts:
        self.api = api
        self.debug = debug

        self.api.gen_auth()

    def get( # pylint: disable=keyword-arg-before-vararg
            self,
            limit: Optional[int] =None,
            *pargs: Optional[list],
            **kwargs: Optional[dict]) -> dict:
        """API: Get list of accounts

        Get a list of all accounts, instantiating Account objects for them

        Args:
           limit (int, optional): Maximum number of accounts to return
           size (int, optional): Number of entries per page to return, default 50 !!kwargs
           offset (int, optional): Page number to get `size` entries !!kwargs

        Returns:
           dict: {`name`: Account()} list of accounts

        Raises:
           None
        """
        accounts: dict = {}

        path = f'{self.api._accounts_path()}/' # pylint: disable=protected-access

        while True:
            # pylint: disable=duplicate-code
            response = self.api.get(path, *pargs, **kwargs)
            assert response.status_code == 200 and response.text
            data = response.json()

            try:
                for account_meta in data['rsMailboxes']:
                    if isinstance(limit, int) and len(accounts) >= limit:
                        raise RetrieveLimit

                    account = Account(account_meta['name'], api=self.api, debug=self.debug).get()
                    assert account is not None

                    accounts.update({account.name.lower(): account})

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
