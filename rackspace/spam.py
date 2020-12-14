from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, List

from .api import Api

import json
import copy

DEBUG = False
VALID_ACL = ('blocklist', 'ipblocklist', 'safelist', 'ipsafelist')

def _positive(x: int) -> None:
    """Ensure the passed in value is a positive integer

    Args:
        x (int): Value to test

    Returns:
        None

    Raises:
        ValueError: on negative values
    """
    if x < 0:
        raise ValueError(f'Value {x!r} is a negative number!')

@dataclass
class Field(object):
    """Field value class

    Field() class helps constrain a value to a specific type,
    handles default value, value constraints and testing
    """
    type: Any = None
    default: Any = None
    valid: Any = None
    test: Any = None
    value: Any = None

    def __repr__(self):
        test = self.test
        if test is not None:
            test = f'{test.__name__}()'
        return f'{self.__class__.__name__}(type={self.type.__name__}, value={self.value!r}, default={self.default!r}, valid={self.valid!r}, test={test})'

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False

        elif self.type != other.type:
            return False

        return self.get() == other.get()

    def default(self) -> Any:
        """Returns the default value of Field

        Args:
            None

        Returns:
            Any: None or defined default value
        """
        return self.default

    def get(self) -> Any:
        """Returns the stored value, or default if no value stored

        Args:
            None

        Returns:
            Any: Stored value, or default value
        """
        if self.value is None:
            return self.default

        return self.value

    def set(self, value) -> None:
        """Stores a value

        Args:
            value: Value to store

        Returns:
            None

        Raises:
            TypeError: `value` is not of required type
            ValueError: `value` is not one of the specified `valid` values
            ValueError: `value` failed the test function
        """
        if value is None:
            self.value = None
            return

        if not isinstance(value, self.type):
            raise TypeError(f'value {value!r} MUST be of type {self.type.__name__!r}')

        if isinstance(self.valid, tuple) and value not in self.valid:
            raise ValueError(f'value {value!r} MUST be one of {self.valid!r}')

        if self.test is not None:
            self.test(value)

        self.value = value

class Spam(object):
    """Spam container object, holds the Settings and ACL objects"""
    def __repr__(self):
        return f'{self.__class__.__name__}(settings={self.settings}, acl={self.acl})'

    def __eq__(self, other):
        if self.settings != other.settings:
            return False

        for acl in set(self.acl) | set(other.acl):
            if acl not in self.acl or acl not in other.acl:
                return False
            if self.acl[acl] != other.acl[acl]:
                return False
        return True

    def __init__(self, *pargs, **kwargs) -> None:
        self.settings = None
        self.acl = {x: None for x in VALID_ACL}

        # Pull data out of kwargs, Settings and ACL need subsets
        # not the full set
        data = kwargs.pop('data', {})

        # Save pargs and kwargs for future calls to Settings and ACL classes
        self.pargs = pargs
        self.kwargs = dict(kwargs)

        # Grab settings object, if config contains settings data
        if 'settings' in data:
            self.settings = Settings(data=data['settings'], *pargs, **kwargs)

        # Grab acl object(s), if config contains acl settings data
        for acl in VALID_ACL:
            if acl in data:
                self.acl[acl] = ACL(acl=acl, data=data[acl], *pargs, **kwargs)
            else:
                self.acl[acl] = None

    def get(self) -> Spam:
        """API: Get all spam settings from rackspace API

        Args:
            None

        Returns:
            Spam: New Spam() object with rackspace settings

        Raises:
            None
        """
        pargs = self.pargs
        kwargs = self.kwargs

        new = Spam(*pargs, **kwargs)

        # Get spam settings from API
        new.settings = self.settings.get()

        # Get ACL settings from API
        for acl in self.acl:
            new.acl[acl] = self.acl[acl].get()

        return new

    def diff(self, other: Spam) -> list:
        """Return difference information between two Spam objects
        
        Args:
            other (Spam): Other Spam() object to compare against

        Returns:
            list: List of tuples with what setting group changed,
                  and optionally what the change data is
        
        Raises:
            None
        """
        diff = []

        # Add settings as a list of changes
        if self.settings != other.settings:
            diff.append('settings')
            ### self.settings.diff(other.settings)

        # Check each acl for changes
        for acl in set(self.acl) | set(other.acl):
            # Not sure this one actually works, it should not
            # be a condition now that we predefine ACL types
            if acl not in other.acl:
                diff.append((acl, {'addList': None},))

            # If the config acl does not match the rackspace acl
            elif self.acl[acl] != other.acl[acl]:
                # Add the acl key, and the actual change state
                diff.append((acl, self.acl[acl].diff(other.acl[acl])))

        return diff

    def set(self, diffs: Optional[list] =None) -> None:
        """API: Sets the setting/acl changes via the API

        Args:
            diffs (list): summary of changes to be published

        Returns:
            None

        Raises:
            None
        """
        if diffs is None or not diffs:
            return

        for diff in diffs:
            # Check if settings have changed and set them
            if diff == 'settings':
                self.settings.set()

            # Tuple sets should be ACL changes
            # (<acl name>,
            #  {'addList': '<comma string of IPs/addresses to add to ACL>',
            #   'removeList': '<comma string of IPs/addresses to remove from from ACL>'})
            elif isinstance(diff, tuple):
                acl, changes = diff
                self.acl[acl].update(changes)

class Settings(object):
    """Object to hold state of spam settings"""
    __DOMAIN_FIELDS = {
            'filterLevel': Field(str, 'on', ('on', 'off', 'exclusive')),
            'overrideUserSettings': Field(bool, False),
            'rsEmail.spamHandling': Field(str, 'toFolder', ('toFolder', 'delete', 'labelSubject', 'toAddress')),
            'rsEmail.hasFolderCleaner': Field(bool, True),
            'rsEmail.spamFolderAgeLimit': Field(int, 7, None, _positive),
            'rsEmail.spamFolderNumLimit': Field(int, 250, None, _positive),
            'rsEmail.spamForwardingAddress': Field(str, ''),
            'exchange.forwardToDomainQuarantine': Field(str, 'off', ('on', 'off', 'nonuser')),
            'exchange.quarantineOwner': Field(str, ''),
            'exchange.removeQuarantineOwner': Field(bool, False),
            'exchange.defaultQuarantineOwner': Field(str, ''),
            'exchange.removeDefaultQuarantineOwner': Field(bool, False),
            }

    __ACCOUNT_RS_FIELDS = {
            'filterLevel': Field(str, 'on', ('on', 'off', 'exclusive')),
            'rsEmail.spamHandling': Field(str, 'toFolder', ('toFolder', 'delete', 'labelSubject', 'toAddress')),
            'rsEmail.hasFolderCleaner': Field(bool, True),
            'rsEmail.spamFolderAgeLimit': Field(int, 7, None, _positive),
            'rsEmail.spamFolderNumLimit': Field(int, 250, None, _positive),
            'rsEmail.spamForwardingAddress': Field(str, ''),
            }

    __ACCOUNT_EX_FIELDS = {
            'filterLevel': Field(str, 'on', ('on', 'off', 'exclusive')),
            'sendtodomainquarantine': Field(bool, False),
            'quarantineowner': Field(str, ''),
            'removeQuarantineOwner': Field(bool, False),
            }

    def __init__(self,
                 api: Optional[Api] =None, 
                 name: Optional[str] =None, 
                 exchange: bool =False, 
                 data: Optional[dict] =None, 
                 debug: bool =DEBUG, 
                 override: bool =False) -> None:
        """Create object for settings

        Args:
            api (Api): API object
            name (str): name of account, or None for domain
            exchange (bool): If this is for an exchange account
            data (dict): Setting data for domain or account
            debug (bool): True for debug mode, no changes written
            override (bool): For domains only, True forces domain settings to all accounts

        Returns:
            None

        Raises:
            None
        """
        self.api = None
        self.name = name
        self.exchange = exchange
        self.debug = debug
        self.override = override

        self._validate_override()

        if api is not None:
            self.api = api

        # Deep Copy to prevent accidential mutable defaults
        # from popping up.  I.E.
        # a = Settings()  from config
        # b = a.get()  get rackspace settings.  This could override
        #              the settings in 'a', because they started from
        #              the same dictionary of objects
        self.settings = copy.deepcopy(self._get_fields())

        if data is not None:
            self.load(data)
        ### for k,v in self.settings.items():
        ###     print(f'{k!r}: {v!r}')

    def __eq__(self, other):
        if len(self.settings) != len(other.settings):
            return False

        if self.__is_exchange() != other.__is_exchange():
            return False

        return self.settings == other.settings

    def _validate_override(self, override: Optional[bool] =None) -> bool:
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
        if override and self.__is_account():
            raise Exception('Cannot set override on user settings')

        return True

    @staticmethod
    def __fix_value(k, v):
        """STATIC: Fix setting values

        Yaml settings turn 'on'/'off' into True/False

        Args:
            k (str): Name of value
            v (Any): Value to fix

        Returns:
            Any: Fixed value

        Raises:
            None
        """
        # Search and fix on/off values
        if k in ('filterLevel', 'forwardToDomainQuarantine'):
            if v is True:
                v = 'on'

            elif v is False:
                v = 'off'

            # Short circuit any other checks
            return v

        return v

    def __is_domain(self) -> bool:
        """Test if the context is domain settings"""
        return self.name is None

    def __is_account(self) -> bool:
        """Test if the context is account settings"""
        return not self.__is_domain()

    def __is_exchange(self) -> bool:
        """Test if the context is an exchange account"""
        return self.exchange

    def diff(self, other: Settings) -> List[tuple]:
        """Generate differences compared to another Settings object

        Args:
            other (Settings): Settings object to compare against

        Returns:
            List[tuple]: Tuples of key, our value, their value

        Raises:
            None
        """
        diff = []
        for k in set(self.settings) | set(other.settings):
            if self.settings[k] != other.settings[k]:
                diff.append((k, self.settings[k].get(), other.settings[k].get()))
                ### print(f'{diff[-1][0]!r}: {diff[-1][1]!r} != {diff[-1][2]!r}')
        return diff

    def load(self, data: dict, src: str ='cfg') -> None:
        """Load settings from dict into our object

        Args:
            data (dict): settings to load
            src (str): Source of our settings (cfg or api)

        Returns:
            None

        Raises:
            None
        """
        # shortcut to reduce typing
        settings = self.settings

        # yaml 'on' becomes True and 'off' becomes False.  These
        # need to stay 'on' and 'off'
        k = 'filterLevel' # another shortcut
        if k in data:
            # save the fixed value in the Field of the setting
            settings[k].set(self.__fix_value(k, data[k]))

        #           ------------- from API --------------  ---- from config ----
        for sub in ('rsEmailSettings', 'exchangeSettings', 'rsEmail', 'exchange'):
            if sub not in data:
                continue

            # exchange accounts don't have a prefix
            if self.__is_account() and self.__is_exchange():
                prefix = ''

            # domain exchange settings are prefixed with 'exchange.'
            elif sub.startswith('exchange'):
                prefix = 'exchange.'

            # domain rsEmail and non-exchange account settings prefixed with 'rsEmail.'
            else:
                prefix = 'rsEmail.'

            ### Don't you love consistent, simplified interfaces.  Wish rackspace had one

            for k,v in data[sub].items():
                # save the fixed value in the Field of the setting
                settings[f'{prefix}{k}'].set(self.__fix_value(k, v))

    def _get_account_path(self) -> str:
        """Get the account path, if we're in an account context

        Args:
            None

        Returns:
            str: Empty string for domain context, else the path segment for accounts

        Raises:
            None
        """
        if self.__is_domain():
            return ''

        # what account path type to use, 'ex' for exchange, 'rs' for rackspace
        qtype = 'ex' if self.exchange else 'rs'

        return f'/{qtype}/mailboxes/{self.name}'

    def get(self, *pargs, **kwargs) -> Settings:
        """API: Get spam settings object from the API

        Args:
            None

        Returns:
            Settings: New Settings object for API spam settings

        Raises:
            None
        """
        account = self._get_account_path()
        path = f'/v1/customers/{self.api.customer}/domains/{self.api.domain}{account}/spam/settings'

        response = self.api.get(path, *pargs, **kwargs)

        if not self.api._success(response):
            return None

        # Probably a better way to do this
        return Settings(api=self.api, name=self.name, data=response.json(), exchange=self.exchange, debug=self.debug)

    def _get_fields(self) -> dict:
        """Get our list of setting fields for this context

        Args:
            None

        Returns:
            dict

        Raises:
            None
        """
        cls = self.__class__

        # Check for domain context
        if self.__is_domain():
            fields = cls.__DOMAIN_FIELDS

        # check for exchange account context
        elif self.__is_exchange():
            fields = cls.__ACCOUNT_EX_FIELDS

        # we should be non-exchange account context
        else:
            fields = cls.__ACCOUNT_RS_FIELDS

        # Ensure we deepcopy so we don't have the mutable defaults propigation bug
        return copy.deepcopy(fields)

    def set(self, override: bool =None, *pargs, **kwargs) -> bool:
        """API: Update any settings changes to the API

        Args:
            override (bool): Domain context only, forces settings to all domain accounts

        Returns:
            bool: Success condition of API call

        Raises:
            None
        """
        account = self._get_account_path()
        path = f'/v1/customers/{self.api.customer}/domains/{self.api.domain}{account}/spam/settings'

        # Default override from object if not passed
        if override is None:
            override = self.override

        self._validate_override(override)

        # must send all values, or things my change in unexpected ways
        # DO NOT try and give only changed settings
        data = dict(self.settings)

        # toFolder is mutually exclusive to 'SpamForwardingAddress'
        if data.get('rsEmail.spamHandling', Field(str, '')).get() == 'toFolder':
            data.pop('rsEmail.spamForwardingAddress')

        # toAddress is mutually exclusive to 'hasFolderCleaner', 'spamFolderAgeLimit' and 'spamFolderNumLimit'
        elif data.get('rsEmail.spamHandling', Field(str, '')).get() == 'toAddress':
            for x in ('hasFolderCleaner', 'spamFolderAgeLimit', 'spamFolderNumLimit'):
                data.pop(f'rsEmail.{x}')

        # Make sure to set the override setting 
        if override:
            data.update({'overrideUserSettings': Field(bool, True)})

        # Convert {k: Field()} to normal {k: v} dict for API call
        data = {k: v.get() for k,v in data.items()}

        if self.debug:
            print(f"\n{path}\n   SPAM SETTINGS SET: '{data}'")
            return True
        else:
            response = self.api.put(path, data, *pargs, **kwargs)
            return self.api._success(response)

class ACL(object):
    """ACL object for spam settings"""
    def __init__(self, 
                 acl: str, 
                 api: Optional[Api] =None, 
                 name: Optional[str] =None, 
                 exchange: bool=False, 
                 data: Any[dict, list] =None, 
                 debug: bool =DEBUG, 
                 *pargs, **kwargs) -> None:
        """Create an ACL object for spam ACLs

        Args:
            acl (str): ACL name, 'blocklist', 'ipblocklist', 'safelist', 'ipsafelist'
            name (str): name of account, or None for domain
            exchange (bool): If this is for an exchange account
            data (dict): ACL settings data
            debug (bool): True for debug mode, no changes written

        Returns:
            None

        Raises:
            None
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

    def __eq__(self, other):
        return set(self.data) == set(other.data)

    def load(self, data: list) -> None:
        """Load config data into this ACL

        Args:
            data (list): List of addresses/IPs to load

        Returns:
            None

        Raises:
            None
        """
        if not isinstance(data, list):
            raise TypeError('ACL must be a list format of addresses or IPs')

        self.data = list(data)

    def _get_account_path(self):
        """Get the account path, if we're in an account context

        Args:
            None

        Returns:
            str: Empty string for domain context, else the path segment for accounts

        Raises:
            None
        """
        if self.name is None:
            return ''

        # what account path type to use, 'ex' for exchange, 'rs' for rackspace
        qtype = 'ex' if self.exchange else 'rs'

        return f'/{qtype}/mailboxes/{self.name}'

    def get(self, *pargs, **kwargs) -> ACL:
        """API: Get spam ACL object from the API

        Args:
            None

        Returns:
            Settings: New ACL object for API spam ACL

        Raises:
            None
        """
        account = self._get_account_path()
        path = f'/v1/customers/{self.api.customer}/domains/{self.api.domain}{account}/spam/{self.acl}'

        response = self.api.get(path, *pargs, **kwargs)

        if not self.api._success(response):
            return None

        # Probably a better way to do this
        return ACL(acl=self.acl, api=self.api, name=self.name, exchange=self.exchange, data=response.json(), debug=self.debug)

    def diff(self, other: ACL) -> Any[dict, None]:
        """Return API compatible difference between this and other ACl object

        Args:
            other (ACL): ACL object to compare against

        Returns:
            dict: API compatible difference between ACLs,
                  None if no differences

        Raises:
            None
        """
        if self == other:
            return None
        
        # Build basic structure, using sets to dedupe addresses/IPs
        diff = {'addList': set(), 'removeList': set()}

        # bi-directional compare
        for k, src, dst in (('addList', self, other), ('removeList', other, self)):
            for x in src.data:
                if x not in dst.data:
                    diff[k].add(x)

        # Use a list, as we are likely to remove keys in-flight
        for k in list(diff):
            v = diff[k]

            # If there are no values, remove the key
            if not v:
                diff.pop(k)

            # convert the values from a set to a comma separated string
            else:
                diff[k] = ','.join(v)

        # return our modified diff
        return diff

    def update(self, data: dict, *pargs, **kwargs) -> bool:
        """API: Update ACL changes with the API

        Args:
            data (dict): differences produced by `.diff()` method

        Returns:
            bool: Success condition of API call

        Raises:
            None
        """
        if not data:
            return True

        account = self._get_account_path()
        path = f'/v1/customers/{self.api.customer}/domains/{self.api.domain}{account}/spam/{self.acl}'

        if self.debug:
            print(f"\n{path}\n   SPAM SETTINGS ACL '{self.acl}': '{data}'")
            return True
        else:
            response = self.api.put(path, data, *pargs, **kwargs)
            return self.api._success(response)

### 
### ### GET /customers/12345678/domains/example.com/spam/settings
### ### {
### ###     "exchangeSettings": {
### ###         "defaultQuarantineOwner": null,
### ###         "forwardToDomainQuarantine": "off",
### ###         "quarantineOwner": ""
### ###     },
### ###     "filterLevel": "on",
### ###     "rsEmailSettings": {
### ###         "hasFolderCleaner": true,
### ###         "spamFolderAgeLimit": 7,
### ###         "spamFolderNumLimit": 250,
### ###         "spamForwardingAddress": "",
### ###         "spamHandling": "toFolder"
### ###     }
### ### }
### 
### ### PUT '/customers/me/domains/example.com/spam/settings',
### ### {
### ###   'filterLevel' => 'on',
### ###   'rsEmail.spamHandling' => 'toFolder',
### ###   'rsEmail.hasFolderCleaner' => 'true',
### ###   'rsEmail.spamFolderAgeLimit' => '7',
### ###   'rsEmail.spamFolderNumLimit' => '100',
### ### }
### ### GET /customers/12345678/domains/example.com/spam/<blocklist | ipblocklist | safelist | ipsafelist>
### ### POST /customers/12345678/domains/example.com/spam/<blocklist | ipblocklist | safelist | ipsafelist>/anyone@spam.com
### ### DELETE /customers/12345678/domains/example.com/spam/<blocklist | ipblocklist | safelist | ipsafelist>/anyone@spam.com
### ### PUT '/customers/12345678/domains/example.com/spam/<blocklist | ipblocklist | safelist | ipsafelist>',
### ### {
### ###   'addList' => '@%.example.com,abc@example.com',
### ###   'removeList' => '@examp%.com'
### ### }
### 
### 
### ### GET /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/settings
### ### PUT /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/settings
### ### {
### ###       'filterLevel' => 'on',  
### ###       'rsEmail.spamHandling' => 'toFolder',
### ###       'rsEmail.hasFolderCleaner' => 'true',
### ###       'rsEmail.spamFolderAgeLimit' => '7',
### ###       'rsEmail.spamFolderNumLimit' => '100',
### ### }
### ### GET /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/<blocklist | ipblocklist | safelist | ipsafelist>
### ### POST /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/<blocklist | ipblocklist | safelist | ipsafelist>/anyone@spam.com
### ### DELETE /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/<blocklist | ipblocklist | safelist | ipsafelist>/anyone@spam.com
### ### PUT /customers/12345678/domains/example.com/rs/mailboxes/alex.smith/spam/<blocklist | ipblocklist | safelist | ipsafelist>
### ### {
### ###   'addList' => '@%.example.com,abc@example.com',
### ###   'removeList' => '@examp%.com'
### ### }
### 
### 
### ### settings:
### ###    filterLevel: on
### ###    rsEmail.spamHandling: toFolder
### ###    rsEmail.hasFolderCleaner: true
### ###    rsEmail.spamFolderAgeLimit: 14
### ###    rsEmail.spamFolderNumLimit: 0
### ###    rsEmail.spamForwardingAddress: ""
### ### blocklist: []
### ### ipblocklist: []
### ### safelist:
### ###   - "@bayphoto.com"
### ###   - "@bounce.email.bayphoto.com"
### ###   - "@email.bayphoto.com"
### ###   - "bounce-350_HTML-13278537-134399-515003010-744@bounce.email.bayphoto.com"
### ###   - "bounce-350_HTML-13278537-136453-515003010-744@bounce.email.bayphoto.com"
### ###   - "bounce-350_HTML-13278537-137710-515003010-744@bounce.email.bayphoto.com"
### ###   - "bounce-350_HTML-13278537-138783-515003010-744@bounce.email.bayphoto.com"
### ###   - "bounce-350_HTML-13278537-147881-515003010-744@bounce.email.bayphoto.com"
### ###   - "bounce-351_HTML-13278537-135299-515003010-744@bounce.email.bayphoto.com"
### ### ipsafelist: []
