from __future__ import annotations

DEBUG = False

class DuplicateLoadError(Exception):
    pass


class RetrieveLimit(Exception):
    pass


class Account(object):
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
            'organizationUnit': str,
            'pagerNumber': str,
            'password': str,
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

    def __init__(self, name: str, data: dict =None, api: Api =None, debug: bool =DEBUG) -> None:
        """Create an Account object

        Instantiate an object of Account

        Args:
           name (str): Name of the account (without domain)
           api (Api, optional): Api object to communicate with rackspace
           data (dict, optional): Data to load into Account object

        Returns:
           None

        Raises:
           None
        """
        self.name = name
        self.loaded = False
        self.debug = debug

        if api is not None:
            self.api = api

        for k,v in self.__class__.__DEFAULTS.items():
            setattr(self, k, v)

        if data:
            self._load(data)

    def __str__(self) -> None:
        data = f'name: "{self.name}"'
        for field in self.__class__.__FIELDS:
            if field == 'name':
                continue

            value = getattr(self, field, None)
            if value is None or value == '':
                continue

            data = f'{data}, {field}: "{value}"'
        data = f'Account({{{data}}})'
        return data

    def __repr__(self) -> None:
        return self.__str__()

    def _load(self, data: dict, _sub=False) -> None:
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

        fields = self.__class__.__FIELDS
        ignore = [ 'aliases', 'spam' ]

        for k,v in data.items():
            if k in ignore:
                continue

            elif k == 'contactInfo':
                self._load(v, _sub=True)
                continue

            ### elif k == 'spam':
            ###     self._load_spam(v)
            ###     continue

            elif k == 'emailForwardingAddressList':
                k = 'enableForwardingAddresses'
                v = ','.join(v)

            if k not in fields:
                print('Unknown field {} found'.format(k))
                continue

            if v is None and fields[k] is str:
                v = ""

            if not isinstance(v, fields[k]):
                if fields[k] is int:
                    v = fields[k](v)
                else:
                    raise TypeError('{} is type {}, instead of type {}'.format(k, type(v), fields[k]))

            # Rackspace likes to sometimes turn empty strings to a single space
            if isinstance(v, str) and v == ' ':
                v = ''

            x = fields[k](v)
            setattr(self, k, x)

        if getattr(self, 'displayName', '') == '':
            fn = getattr(self, 'firstName', '')
            ln = getattr(self, 'lastName', '')
            if fn or ln:
                setattr(self, 'displayName', ' '.join((fn, ln)).strip())

        # Only the parent call is allowed to set the loaded flag
        if _sub is False:
            self.loaded=True

    def diff(self, other_account: Account) -> dict:
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
        fields = self.__class__.__FIELDS
        readonly = self.__class__.__READONLY
        ignore = ['password', 'recoverDeleted', 'name', 'spam']

        ### if getattr(self, 'name') != getattr(other_account, 'name'):
        ###     raise Exception("Must compare same accounts")

        diff = {}
        for field in fields:
            if field in readonly or field in ignore:
                continue

            if fields[field] is str:
                default = ''
            elif fields[field] is int:
                default = 0
            elif fields[field] is bool:
                default = False

            v1 = getattr(self, field, default)
            v2 = getattr(other_account, field, default)
            if v1 != v2:
                ### print(f"DIFF: {field}; '{v1}' != '{v2}'")
                diff.update({field: v1})

        return diff

    def get(self, *pargs: list, **kwargs: dict) -> Account:
        """API: Get the account data from rackspace

        Calls the rackspace API to retrieve the account data

        Args:

        Returns:
           Account: on success, a NEW Account object, created from rackspace data
                    else, None

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}'

        response = self.api.get(path, *pargs, **kwargs)

        if not self.api._success(response):
            return None

        return Account(self.name, api=self.api, data=response.json())

    def add(self, data: dict =None, *pargs: list, **kwargs: dict) -> bool:
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
        path = f'{self.api._account_path(self.name)}'

        fields = self.__class__.__FIELDS
        readonly = self.__class__.__READONLY
        required = self.__class__.__ADD_REQUIRED

        if data is None:
            data = {}
            for field, data_type in fields.items():
                if field in readonly:
                    continue
                
                if data_type is str:
                    default = ''
                elif data_type is int:
                    default = 0
                elif data_type is bool:
                    default = False

                data[field] = getattr(self, field, default)

        FAILED = False
        for req in required:
            if req not in data:
                print(f"Required field {req} missing")
                FAILED = True
        if FAILED:
            raise LookupError('Data missing required fields to add account')

        if self.debug:
            print(f"\n{path}\n   ACCOUNT ADD: '{self.name}'")
        else:
            response = self.api.post(path, data, *pargs, **kwargs)
            return self.api._success(response)

    def remove(self, *pargs: list, **kwargs: dict) -> bool:
        """API: Remove the account from rackspace

        Removes the account from rackspace

        Args:

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}'

        if self.debug:
            print(f"\n{path}\n   ACCOUNT REMOVE: '{self.name}'")
        else:
            response = self.api.delete(path, *pargs, **kwargs)
            return self.api._success(response)

    def rename(self, newname: str, *pargs: list, **kwargs: dict) -> bool:
        """API: Rename the account in rackspace

        Renames the account to a new account name

        Args:
           newname (str): New account name (without domain)

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}'

        if self.debug:
            print(f"\n{path}\n   ACCOUNT RENAME: '{self.name}' -> '{newname}'")
        else:
            response = self.api.put(path, data={'name': newname}, *pargs, **kwargs)
            return self.api._succes_success(response)

    def update(self, data: dict, *pargs: list, **kwargs: dict) -> bool:
        """API: Update the account in rackspace

        Updates the rackspace account, setting the fields to match `data` or self attributes

        Args:
           data (dict, optional): Data to set on the rackspace account

        Returns:
           bool: True on success

        Raises:
           None
        """
        path = f'{self.api._account_path(self.name)}'

        if self.debug:
            print(f"\n{path}\n   ACCOUNT UPDATE: '{self.name}' => {data}")
        else:
            response = self.api.put(path, data=data, *pargs, **kwargs)
            return self.api._success(response)


class Accounts(object):
    def __init__(self, api: Api, debug: bool =DEBUG) -> None:
        self.api = api
        self.debug = debug

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

                    account = Account(account_meta['name'], api=self.api, debug=self.debug).get()
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
