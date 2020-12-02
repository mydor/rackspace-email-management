from __future__ import annotations

class Account(object):
    __defaults = {
            'size': 25600,
            'enabled': True,
            'visibleInRackspaceEmailCompanyDirectory': True,
            'visibleInExchangeGAL': True,
            }

    __fields = {
            'password': str,
            'size': int,
            'recoverDeleted': bool,
            'enableVacationMessage': bool,
            'vacationMessage': str,
            'enableForwardingAddresses': str,
            'saveForwardedEmail': bool,
            'lastName': str,
            'firstName': str,
            'generationQualifier': str,
            'initials': str,
            'displayName': str,
            'organizationUnit': str,
            'businessNumber': str,
            'pagerNumber': str,
            'homeNumber': str,
            'mobileNumber': str,
            'faxNumber': str,
            'homeFaxNumber': str,
            'businessStreet': str,
            'businessCity': str,
            'businessState': str,
            'businessPostalCode': str,
            'businessCountry': str,
            'homeStreet': str,
            'homeCity': str,
            'homeState': str,
            'homePostalCode': str,
            'homeCountry': str,
            'notes': str,
            'title': str,
            'userID': str,
            'organizationalStatus': str,
            'employeeType': str,
            'customID': str,
            'enabled': bool,
            'visibleInRackspaceEmailCompanyDirectory': bool,
            'visibleInExchangeGAL': bool,
            'currentUsage': int,
            'createdDate': str,
            'lastLogin': str,
            'name': str,
            }

    __readonly = [
            'currentUsage',
            'createdDate',
            'lastLogin',
            'name',
            ]

    __add_required = [
            'password',
            'size',
            ]

    def _load(self: Account, data: dict) -> None:
        fields = self.__class__.__fields
        ignore = [ 'aliases' ]
        defaults = self.__class__.__defaults

        for k,v in defaults.items():
            setattr(self, k, v)

        for k,v in data.items():
            if k in ignore:
                continue

            elif k == 'contactInfo':
                self._load(v)
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

    def __str__(self: Account) -> None:
        return f'''{{name: "{self.name}", enabled: {self.enabled}, size: {self.size}, displayName: "{self.displayName}"}}'''

    def __repr__(self: Account) -> None:
        return self.__str__()

    def __init__(self: Account, data: dict, api=None) -> None:
        self._load(data)

        if api is not None:
            self.api = api

        if getattr(self, 'displayName', None) is None:
            fn = getattr(self, 'firstName', '')
            ln = getattr(self, 'lastName', '')
            if fn or ln:
                setattr(self, 'displayName', ' '.join((fn, ln)).strip())

    def diff(self: Account, other_account: Account) -> dict:
        # Accounts all contain the exact same keys that each only have
        # a single value, no lists or dicts
        # Thus, we are only concerned with what needs to be changed,
        # don't have to worry about what to remove as with Alias objects
        fields = self.__class__.__fields
        readonly = self.__class__.__readonly
        ignore = ['password', 'recoverDeleted', 'name']

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

    ### @staticmethod
    ### def _success(response: requests.Response, status_code: int =200) -> bool:
    ###     if response.status_code != status_code:
    ###         if response.text:
    ###             print(json.dumps(response.json(), sort_keys=True, indent=4))
    ###         return False
    ###     return True

    def add(self: Account, data: dict =None, *pargs: list, **kwargs: dict) -> bool:
        path = f'{self.api._account_path(self.name)}'

        fields = self.__class__.__fields
        readonly = self.__class__.__readonly
        required = self.__class__.__add_required

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

        print(f"\n{path}\n   ACCOUNT ADD: '{self.name}'")
        ### response = self.api.post(path, data, *pargs, **kwargs)
        ### return self.api._success(response)

    def remove(self: Account, *pargs: list, **kwargs: dict) -> bool:
        path = f'{self.api._account_path(self.name)}'

        print(f"\n{path}\n   ACCOUNT REMOVE: '{self.name}'")
        #response = self.api.delete(path, *pargs, **kwargs)
        #return self.api._success(response)

    def rename(self: Account, newname: str, *pargs: list, **kwargs: dict) -> bool:
        path = f'{self.api._account_path(self.name)}'

        print(f"\n{path}\n   ACCOUNT RENAME: '{self.name}' -> '{newname}'")
        ### response = self.api.put(path, data={'name': newname}, *pargs, **kwargs)
        ### return self.api._succes_success(response)

    def update(self: Account, data: dict, *pargs: list, **kwargs: dict) -> bool:
        path = f'{self.api._account_path(self.name)}'

        print(f"\n{path}\n   ACCOUNT UPDATE: '{self.name}' => {data}")
        ### response = self.api.put(path, data=data, *pargs, **kwargs)
        ### return self.api._success(response)
