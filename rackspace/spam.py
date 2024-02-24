"""Handle RackSpace spam settings"""
from __future__ import annotations

import copy
import json

from dataclasses import dataclass
from typing import Any, Optional, List, TypeVar, Union, Callable

from .api import Api

SelfSpam = TypeVar('SelfSpam', bound='Spam')
SelfSettings = TypeVar('SelfSettings', bound='Settings')
SelfACL = TypeVar('SelfACL', bound='ACL') # pylint: disable=invalid-name

# NOTE: Spam settings are stored in 5 separate endpoints each, for
# both domains AND accounts.  These consist of the 'settings',
# and ACL lists 'blocklist', 'ipblocklist', 'safelist', and 'ipsafelist'
#
# Domain spam settings include both Rackspace Email spam settings
# AND exchange spam settings.
#
# Account spam settings are EITHER Rackspace Email spam settings,
# OR exchange spam settings, depending on the context of the account

DEBUG = False
VALID_ACL = ('blocklist', 'ipblocklist', 'safelist', 'ipsafelist')

def _positive(x: int) -> None:
    """Ensure the passed in value is a positive integer

    Args:
        x (int): Value to test

    Raises:
        ValueError: on negative values
    """
    if x < 0:
        raise ValueError(f'Value {x!r} is a negative number!')

@dataclass
class Field():
    """Field value class

    Field() class helps constrain a value to a specific type,
    handles default value, value constraints and testing
    """
    __type: Union[str, int, bool]
    __default: Union[str, int, bool, None] = None
    __valid: tuple[Union[str, int, bool]] = None
    __test: Callable = None
    __value: Union[str, int, bool, None] = None

    def __str__(self) -> str:
        return str(self.__value)

    def __repr__(self) -> str:
        test = self.__test
        if test is not None:
            test = f'{test.__name__}()'
        return (f'{self.__class__.__name__}(' +
            ', '.join((
                f'type={self.__type.__name__!r}',
                f'value={self.value!r}',
                f'default={self.__default!r}',
                f'valid={self.__valid!r}',
                f'test={test})'
            )))

    def __eq__(
            self,
            other) -> bool:
        if self.__class__ != other.__class__:
            return False

        if self.type != other.type:
            return False

        return self.value == other.value

    @property
    def type(self) -> Union[str, int, bool]:
        """
        Get <Field> type constraint

        Returns:
            Union[str, int, bool]: expected object value's type
        """
        return self.__type

    @property
    def default(self) -> Optional[Union[str, int, bool]]:
        """Returns the default value of Field

        Returns:
            Any: None or defined default value
        """
        print("<Field>.default should only be used for debugging!!!")
        return self.__default

    @property
    def value(self) -> Optional[Union[str, int, bool]]:
        """
        Get <Field>'s value, or if not set, the default

        Returns:
            Optional[Union[str, int, bool]]: <Field> value or default
        """
        if self.__value is None:
            return self.__default

        return self.__value

    @value.setter
    def value(self, value) -> None:
        if value is None:
            self.__value = None
            return

        if not isinstance(value, self.__type):
            raise TypeError(f'value {value!r} MUST be of type {self.__type.__name__!r}')

        if isinstance(self.__valid, tuple) and value not in self.__valid:
            raise ValueError(f'value {value!r} MUST be one of {self.__valid!r}')

        if self.__test is not None:
            self.__test(value)

        self.__value = value

    @property
    def valid(self) -> Any:
        """
        Get <Field> valid possible settings

        Returns:
            Any: tuple of valid valued
        """
        print("<Field>.valid should only be used for debugging!!!")
        return self.__valid

    @property
    def test(self) -> Callable:
        """
        Get <Field>'s value validation function

        Returns:
            Callable: Value validation function
        """
        print("<Field>.test should only be used for debugging!!!")
        return self.__test

    def get(self) -> Any:
        """Returns the stored value, or default if no value stored

        Returns:
            Any: Stored value, or default value
        """
        print("Something calling `.get()`, should use `.value`")
        return self.value
        # if self.value is None:
        #     return self.__default

        # return self.value


    def set(self, value) -> None:
        """Stores a value

        Args:
            value: Value to store

        Raises:
            TypeError: `value` is not of required type
            ValueError: `value` is not one of the specified `valid` values
            ValueError: `value` failed the test function
        """
        print("Something calling `.set(<value>)`, should use `.value = <value>`")
        self.value = value
        # if value is None:
        #     self.__value = None
        #     return

        # if not isinstance(value, self.__type):
        #     raise TypeError(f'value {value!r} MUST be of type {self.__type.__name__!r}')

        # if isinstance(self.__valid, tuple) and value not in self.__valid:
        #     raise ValueError(f'value {value!r} MUST be one of {self.__valid!r}')

        # if self.__test is not None:
        #     self.__test(value)

        # self.__value = value

class Spam():
    """Spam container object, holds the Settings and ACL objects"""
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(settings={self.data}, acl={self.acl})'

    def __eq__(
            self,
            other) -> bool:
        if self.data != other.data:
            return False

        for acl in set(self.acl) | set(other.acl):
            if acl not in self.acl or acl not in other.acl:
                return False
            if self.acl[acl] != other.acl[acl]:
                return False
        return True

    def __init__(
            self,
            *pargs,
            **kwargs) -> SelfSpam:
        self.data = None
        self.acl = {x: None for x in VALID_ACL}

        # Pull data out of kwargs, Settings and ACL need subsets
        # not the full set
        data = kwargs.pop('data', {})

        # Save pargs and kwargs for future calls to Settings and ACL classes
        self.pargs = pargs
        self.kwargs = dict(kwargs)

        # Grab settings object, if config contains settings data
        if 'settings' in data:
            self.data = Settings(data=data['settings'], *pargs, **kwargs)

        # Grab acl object(s), if config contains acl settings data
        for acl in VALID_ACL:
            if acl in data:
                self.acl[acl] = ACL(acl=acl, data=data[acl], *pargs, **kwargs)
            else:
                self.acl[acl] = None

    def get(self) -> Spam:
        """API: Get all spam settings from rackspace API

        Returns:
            Spam: New Spam() object with rackspace settings
        """
        pargs = self.pargs
        kwargs = self.kwargs

        new = Spam(*pargs, **kwargs)

        # Get spam settings from API
        if self.data is not None:
            new.data = self.data.get()

        # Get ACL settings from API
        for acl in self.acl:
            if self.acl[acl] is not None:
                new.acl[acl] = self.acl[acl].get()

        return new

    def diff(
            self,
            other: Spam) -> list:
        """Return difference information between two Spam objects

        Args:
            other (Spam): Other Spam() object to compare against

        Returns:
            list: List of tuples with what setting group changed,
                  and optionally what the change data is
        """
        diff = []

        # Short-circuit settings tests if either doesn't have 'settings'
        if getattr(self, 'settings', None) is None or getattr(other, 'settings', None) is None:
            pass

        # Add settings as a list of changes
        elif self.data != other.data:
            diff.append('settings')

        # Check each acl for changes
        for acl in set(self.acl) | set(other.acl):
            # Not sure this one actually works, it should not
            # be a condition now that we predefine ACL types
            if acl not in other.acl:
                diff.append((acl, {'addList': None},))

            elif acl not in self.acl:
                diff.append((acl, {'removeLisst': other.acl[acl].data}))

            # If the config acl does not match the rackspace acl
            elif self.acl[acl] != other.acl[acl]:
                # Add the acl key, and the actual change state
                diff.append((acl, self.acl[acl].diff(other.acl[acl])))

        return diff

    def set(
            self,
            diffs: Optional[list] =None) -> None:
        """API: Sets the setting/acl changes via the API

        Args:
            diffs (list): summary of changes to be published
        """
        if diffs is None or not diffs:
            return

        for diff in diffs:
            # Check if settings have changed and set them
            if diff == 'settings' and self.data is not None:
                self.data.set()

            # Tuple sets should be ACL changes
            # (<acl name>,
            #  {'addList': '<comma string of IPs/addresses to add to ACL>',
            #   'removeList': '<comma string of IPs/addresses to remove from from ACL>'})
            elif isinstance(diff, tuple):
                acl, changes = diff
                if self.acl[acl] is not None:
                    self.acl[acl].update(changes)

class Settings():
    """Object to hold state of spam settings"""
    __DOMAIN_FIELDS = {
            'filterLevel': Field(str,
                                 'on',
                                 ('on', 'off', 'exclusive')),
            'overrideUserSettings': Field(bool, False),
            'rsEmail.spamHandling': Field(str,
                                          'toFolder',
                                          ('toFolder', 'delete', 'labelSubject', 'toAddress')),
            'rsEmail.hasFolderCleaner': Field(bool, True),
            'rsEmail.spamFolderAgeLimit': Field(int,
                                                7,
                                                None,
                                                _positive),
            'rsEmail.spamFolderNumLimit': Field(int,
                                                250,
                                                None,
                                                _positive),
            'rsEmail.spamForwardingAddress': Field(str, ''),
            'exchange.forwardToDomainQuarantine': Field(str,
                                                        'off',
                                                        ('on', 'off', 'nonuser')),
            'exchange.quarantineOwner': Field(str, ''),
            'exchange.removeQuarantineOwner': Field(bool, False),
            'exchange.defaultQuarantineOwner': Field(str, ''),
            'exchange.removeDefaultQuarantineOwner': Field(bool, False),
            }

    __ACCOUNT_RS_FIELDS = {
            'filterLevel': Field(str,
                                 'on',
                                 ('on', 'off', 'exclusive')),
            'rsEmail.spamHandling': Field(str,
                                          'toFolder',
                                          ('toFolder', 'delete', 'labelSubject', 'toAddress')),
            'rsEmail.hasFolderCleaner': Field(bool, True),
            'rsEmail.spamFolderAgeLimit': Field(int,
                                                7,
                                                None,
                                                _positive),
            'rsEmail.spamFolderNumLimit': Field(int,
                                                250,
                                                None,
                                                _positive),
            'rsEmail.spamForwardingAddress': Field(str, ''),
            }

    __ACCOUNT_EX_FIELDS = {
            'filterLevel': Field(str,
                                 'on',
                                 ('on', 'off', 'exclusive')),
            'sendtodomainquarantine': Field(bool, False),
            'quarantineowner': Field(str, ''),
            'removeQuarantineOwner': Field(bool, False),
            }

    def __repr__(self) -> str:
        data = {key: val.value for key,val in self.data.items()}
        data = json.dumps(data, sort_keys=True)
        return (f'{self.__class__.__name__}(' +
                ', '.join((
                    f'name={self.name!r}',
                    f'exchange={self.exchange}',
                    f'override={self.override}',
                    f'data={data})'
                )))

    def __init__( # pylint: disable=too-many-arguments
            self,
            api: Optional[Api] =None,
            name: str =None,
            exchange: bool =False,
            data: Optional[dict] =None,
            debug: bool =DEBUG,
            override: bool =False) -> SelfSettings:
        """Create object for settings

        Args:
            api (Api): API object
            name (str): name of account, or None for domain
            exchange (bool): If this is for an exchange account
            data (dict): Setting data for domain or account
            debug (bool): True for debug mode, no changes written
            override (bool): For domains only, True forces domain settings to all accounts

        Returns:
            Settings: Instance of Settings
        """
        self.api = None
        self.name = name
        self.exchange = exchange
        self.debug = debug
        self.override = override

        self._validate_override()

        if api is not None:
            self.api = api

        self.data = self._get_fields()

        if data is not None:
            self.load(data)

    def __eq__(
            self,
            other) -> bool:
        if len(self.data) != len(other.data):
            return False

        if self.is_exchange != other.is_exchange:
            return False

        return self.data == other.data

    def _validate_override(
            self,
            override: Optional[bool] =None) -> bool:
        """Validate if override is valid in context

        Args:
            override (bool): Override flag

        Return:
            bool: True if override is valid

        Raises:
            Exception: Invalid context for override
        """
        # Grab object's override if not passed in
        if override is None:
            override = self.override

        # override is not valid in account context
        if override and self.is_account:
            # pylint: disable=broad-exception-raised
            raise Exception('Cannot set override on user settings')

        return True

    @staticmethod
    def __fix_value(
            key: str,
            val: Any) -> Any:
        """STATIC: Fix setting values

        Yaml settings turn 'on'/'off' into True/False

        Args:
            key (str): Name of value
            val (Any): Value to fix

        Returns:
            Any: Fixed value
        """
        # Search and fix on/off values
        if key in ('filterLevel', 'forwardToDomainQuarantine'):
            if val is True:
                val = 'on'

            elif val is False:
                val = 'off'

            # Short circuit any other checks
            return val

        return val

    @property
    def is_domain(self) -> bool:
        """Test if the context is domain settings"""
        return self.name is None

    @property
    def is_account(self) -> bool:
        """Test if the context is account settings"""
        return not self.is_domain

    @property
    def is_exchange(self) -> bool:
        """Test if the context is an exchange account"""
        return self.exchange

    def diff(
            self,
            other: Settings) -> List[tuple]:
        """Generate differences compared to another Settings object

        Args:
            other (Settings): Settings object to compare against

        Returns:
            List[tuple]: Tuples of key, our value, their value
        """
        diff = []
        for key in set(self.data) | set(other.data):
            if self.data[key] != other.data[key]:
                diff.append((key, self.data[key].value, other.data[key].value))
        return diff

    def load( # pylint: disable=unused-argument
            self,
            data: dict,
            src: str ='cfg') -> None:
        """Load settings from dict into our object

        Args:
            data (dict): settings to load
            src (str): Source of our settings (cfg or api)
        """
        settings = self.data

        # yaml 'on' becomes True and 'off' becomes False.  These
        # need to stay 'on' and 'off'
        key = 'filterLevel'
        if key in data:
            # save the fixed value in the Field of the setting
            settings[key].value = self.__fix_value(key, data[key])

        #           ------------- from API --------------  ---- from config ----
        for sub in ('rsEmailSettings', 'exchangeSettings', 'rsEmail', 'exchange'):
            if sub not in data:
                continue

            # exchange accounts don't have a prefix
            if self.is_account and self.is_exchange:
                prefix = ''

            # domain exchange settings are prefixed with 'exchange.'
            elif sub.startswith('exchange'):
                prefix = 'exchange.'

            # domain rsEmail and non-exchange account settings prefixed with 'rsEmail.'
            else:
                prefix = 'rsEmail.'

            ### Don't you love consistent, simplified interfaces.  Wish rackspace had one

            for key, val in data[sub].items():
                # save the fixed value in the Field of the setting
                settings[f'{prefix}{key}'].value = self.__fix_value(key, val)

    def _get_account_path(self) -> str:
        """Get the account path, if we're in an account context

        Returns:
            str: Empty string for domain context, else the path segment for accounts
        """
        if self.is_domain:
            return ''

        # what account path type to use, 'ex' for exchange, 'rs' for rackspace
        qtype = 'ex' if self.exchange else 'rs'

        return f'{qtype}/mailboxes/{self.name}'

    def get(
            self,
            *pargs,
            **kwargs) -> Optional[Settings]:
        """API: Get spam settings object from the API

        Returns:
            Settings: New Settings object for API spam settings
        """
        account = self._get_account_path()
        path = '/'.join((
            '', # Force leading /
            'v1',
            'customers',
            str(self.api.customer),
            'domains',
            self.api.domain,
            account,
            'spam',
            'settings'
        ))
        # path = f'/v1/customers/{self.api.customer}/domains/{self.api.domain}/{account}/spam/settings'

        response = self.api.get(path, *pargs, **kwargs)

        if not self.api._success(response): # pylint: disable=protected-access
            return None

        # Probably a better way to do this
        return Settings(
            api=self.api,
            name=self.name,
            data=response.json(),
            exchange=self.exchange,
            debug=self.debug)

    def _get_fields(self) -> dict:
        """Get our list of setting fields for this context

        Returns:
            dict: Copy of the fields
        """
        cls = self.__class__

        # Check for domain context
        if self.is_domain:
            fields = cls.__DOMAIN_FIELDS # pylint: disable=protected-access

        # check for exchange account context
        elif self.is_exchange:
            fields = cls.__ACCOUNT_EX_FIELDS # pylint: disable=protected-access

        # we should be non-exchange account context
        else:
            fields = cls.__ACCOUNT_RS_FIELDS # pylint: disable=protected-access

        # Deep Copy to prevent accidential mutable defaults
        # from popping up.  I.E.
        # a = Settings()  from config
        # b = a.value  get rackspace settings.  This could override
        #              the settings in 'a', because they started from
        #              the same dictionary of objects
        return copy.deepcopy(fields)

    def set(
            self,
            *pwargs,
            **kwargs):
        """
        Unknown

        Returns:
            _type_: _description_
        """
        print(f'{self.__class__.__name__}.set() is called, but appears to be recursive')
        return self.set(*pwargs, **kwargs)

    def update( # pylint: disable=keyword-arg-before-vararg
            self,
            override: Optional[bool] =None,
            *pargs,
            **kwargs) -> bool:
        """API: Update any settings changes to the API

        Args:
            override (bool): Domain context only, forces settings to all domain accounts

        Returns:
            bool: Success condition of API call
        """
        account = self._get_account_path()
        path = '/'.join((
            '', # Force leading /
            'v1',
            'customers',
            str(self.api.customer),
            'domains',
            self.api.domain,
            account,
            'spam',
            'settings'
        ))
        # path = f'/v1/customers/{self.api.customer}/domains/{self.api.domain}/{account}/spam/settings'

        if override is None:
            override = self.override

        self._validate_override(override)

        # must send all values, or things my change in unexpected ways
        # DO NOT try and give only changed settings
        data = dict(self.data)

        # toFolder is mutually exclusive to 'SpamForwardingAddress'
        if data.get('rsEmail.spamHandling', Field(str, '')).value == 'toFolder':
            data.pop('rsEmail.spamForwardingAddress')

        # toAddress is mutually exclusive to 'hasFolderCleaner', 'spamFolderAgeLimit' and 'spamFolderNumLimit' # pylint: disable=line-too-long
        elif data.get('rsEmail.spamHandling', Field(str, '')).value == 'toAddress':
            for x in ('hasFolderCleaner', 'spamFolderAgeLimit', 'spamFolderNumLimit'):
                data.pop(f'rsEmail.{x}')

        # Make sure to set the override setting, if set
        if override:
            data.update({'overrideUserSettings': Field(bool, True)})

        # Convert {key: Field()} to normal {key: val} dict for API call
        data = {key: val.value for key,val in data.items()}

        if self.debug:
            print(f"\n{path}\n   SPAM SETTINGS SET: '{data}'")
            return True

        response = self.api.put(path, data, *pargs, **kwargs)
        return self.api._success(response) # pylint: disable=protected-access

class ACL():
    """ACL object for spam settings"""
    def __repr__(self) -> str:
        data = json.dumps(sorted(self.data), sort_keys=True)
        return (f'{self.__class__.__name__}(' +
                ', '.join((
                    f'acl={self.acl!r}',
                    f'name={self.name!r}',
                    f'exchange={self.exchange}',
                    f'data={data})'
                )))

    def __eq__(self, other) -> bool:
        return set(self.data) == set(other.data)

    def __init__( # pylint: disable=too-many-arguments,keyword-arg-before-vararg,unused-argument
            self,
            acl: str,
            api: Optional[Api] = None,
            name: Optional[str] = None,
            exchange: Optional[bool] = False,
            data: Any[dict, list] = None,
            debug: Optional[bool] = DEBUG,
            *pargs,
            **kwargs) -> SelfACL:
        """Create an ACL object for spam ACLs

        Args:
            acl (str): ACL name, 'blocklist', 'ipblocklist', 'safelist', 'ipsafelist'
            name (str): name of account, or None for domain
            exchange (bool): If this is for an exchange account
            data (dict): ACL settings data
            debug (bool): True for debug mode, no changes written
        """
        self.api = api
        self.name = name
        self.data = []
        self.debug = debug
        self.exchange = exchange

        if acl not in VALID_ACL:
            raise ValueError(f"acl '{acl}' must be one of {VALID_ACL}")

        self.acl = acl

        if data is not None:
            # API is subindexed by 'addresses'
            if 'addresses' in data:
                self.load(data['addresses'])

            # Cfg data is just a list of addresses
            else:
                self.load(data)

    def load(
            self,
            data: list) -> None:
        """Load config data into this ACL

        Args:
            data (list): List of addresses/IPs to load
        """
        if not isinstance(data, list):
            raise TypeError('ACL must be a list format of addresses or IPs')

        self.data = list(set(data))

    def _get_account_path(self) -> str:
        """Get the account path, if we're in an account context

        Returns:
            str: Empty string for domain context, else the path segment for accounts
        """
        if self.name is None:
            return ''

        # what account path type to use, 'ex' for exchange, 'rs' for rackspace
        qtype = 'ex' if self.exchange else 'rs'

        return f'/{qtype}/mailboxes/{self.name}'

    def get(
            self,
            *pargs,
            **kwargs) -> ACL:
        """API: Get spam ACL object from the API

        Returns:
            Settings: New ACL object for API spam ACL
        """
        account = self._get_account_path()
        path = '/'.join((
            '', # force leading /
            'v1',
            'customers',
            str(self.api.customer),
            'domains',
            self.api.domain,
            account,
            'spam',
            self.acl
        ))
        # path = f'/v1/customers/{self.api.customer}/domains/{self.api.domain}/{account}/spam/{self.acl}'

        response = self.api.get(path, *pargs, **kwargs)

        if not self.api._success(response): # pylint: disable=protected-access
            return None

        # Probably a better way to do this
        return ACL(acl=self.acl,
                   api=self.api,
                   name=self.name,
                   exchange=self.exchange,
                   data=response.json(),
                   debug=self.debug)

    def diff(
            self,
            other: ACL) -> Optional[dict]:
        """Return API compatible difference between this and other ACl object

        Args:
            other (ACL): ACL object to compare against

        Returns:
            dict: API compatible difference between ACLs,
                  None if no differences
        """
        if self == other:
            return None

        # Build basic structure, using sets to dedupe addresses/IPs
        diff = {'addList': set(), 'removeList': set()}

        # bi-directional compare
        for key, src, dst in (('addList', self, other), ('removeList', other, self)):
            for x in src.data:
                if x not in dst.data:
                    diff[key].add(x)

        # Use a list, as we are likely to remove keys in-flight
        for key in list(diff):
            val = diff[key]

            if not val:
                diff.pop(key)

            else:
                diff[key] = ','.join(val)

        # return our modified diff
        return diff

    def set(
            self,
            *pargs,
            **kwargs) -> bool:
        """See .update()"""
        return self.update(*pargs, **kwargs)

    def update(
            self,
            data: dict,
            *pargs,
            **kwargs) -> bool:
        """API: Update ACL changes with the API

        Args:
            data (dict): differences produced by `.diff()` method

        Returns:
            bool: Success condition of API call
        """
        if not data:
            return True

        account = self._get_account_path()
        path = '/'.join((
            '', # Force leading /
            'v1',
            'customers',
            str(self.api.customer),
            'domains',
            self.api.domain,
            account,
            'spam',
            self.acl
        ))
        # path = f'/v1/customers/{self.api.customer}/domains/{self.api.domain}/{account}/spam/{self.acl}'

        if self.debug:
            print(f"\n{path}\n   SPAM SETTINGS ACL '{self.acl}': '{data}'")
            return True

        response = self.api.put(path, data, *pargs, **kwargs)
        return self.api._success(response) # pylint: disable=protected-access


### GET /customers/12345678/domains/example.com/spam/settings
### {
###     "exchangeSettings": {
###         "defaultQuarantineOwner": null,
###         "forwardToDomainQuarantine": "off",
###         "quarantineOwner": ""
###     },
###     "filterLevel": "on",
###     "rsEmailSettings": {
###         "hasFolderCleaner": true,
###         "spamFolderAgeLimit": 7,
###         "spamFolderNumLimit": 250,
###         "spamForwardingAddress": "",
###         "spamHandling": "toFolder"
###     }
### }

### PUT '/customers/me/domains/example.com/spam/settings',
### {
###   'filterLevel' => 'on',
###   'rsEmail.spamHandling' => 'toFolder',
###   'rsEmail.hasFolderCleaner' => 'true',
###   'rsEmail.spamFolderAgeLimit' => '7',
###   'rsEmail.spamFolderNumLimit' => '100',
### }
### GET /customers/12345678/domains/example.com/spam/<blocklist | ipblocklist | safelist | ipsafelist>
### POST /customers/12345678/domains/example.com/spam/<blocklist | ipblocklist | safelist | ipsafelist>/anyone@spam.com
### DELETE /customers/12345678/domains/example.com/spam/<blocklist | ipblocklist | safelist | ipsafelist>/anyone@spam.com
### PUT '/customers/12345678/domains/example.com/spam/<blocklist | ipblocklist | safelist | ipsafelist>',
### {
###   'addList' => '@%.example.com,abc@example.com',
###   'removeList' => '@examp%.com'
### }


### GET /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/settings
### PUT /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/settings
### {
###       'filterLevel' => 'on',
###       'rsEmail.spamHandling' => 'toFolder',
###       'rsEmail.hasFolderCleaner' => 'true',
###       'rsEmail.spamFolderAgeLimit' => '7',
###       'rsEmail.spamFolderNumLimit' => '100',
### }
### GET /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/<blocklist | ipblocklist | safelist | ipsafelist>
### POST /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/<blocklist | ipblocklist | safelist | ipsafelist>/anyone@spam.com
### DELETE /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/<blocklist | ipblocklist | safelist | ipsafelist>/anyone@spam.com
### PUT /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/<blocklist | ipblocklist | safelist | ipsafelist>
### {
###   'addList' => '@%.example.com,abc@example.com',
###   'removeList' => '@examp%.com'
### }


### settings:
###    filterLevel: on
###    rsEmail.spamHandling: toFolder
###    rsEmail.hasFolderCleaner: true
###    rsEmail.spamFolderAgeLimit: 14
###    rsEmail.spamFolderNumLimit: 0
###    rsEmail.spamForwardingAddress: ""
### blocklist: []
### ipblocklist: []
### safelist:
###   - "@bayphoto.com"
###   - "@bounce.email.bayphoto.com"
###   - "@email.bayphoto.com"
###   - "bounce-350_HTML-13278537-134399-515003010-744@bounce.email.bayphoto.com"
### ipsafelist: []
