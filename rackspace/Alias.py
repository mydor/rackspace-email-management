from __future__ import annotations

class Alias(object):
    def __str__(self: Alias) -> None:
        return f'''{{name: "{self.name}", addresses: ["{'", "'.join(self.addresses)}"]}}'''

    def __repr__(self: Alias) -> None:
        return self.__str__()

    def __init__(self: Alias, data: dict =None, name: str =None, address: str =None, api=None) -> None:
        if api is not None:
            self.api = api

        if name is not None and address is not None:
            self.name = name
            self.addresses = [address]
            return

        self.name = data['name']


        if all(key in data for key in ('numberOfMembers', 'singleMemberName')) and data['numberOfMembers'] == 1:
            self.addresses = [ data['singleMemberName'] ]

        elif all(key in data for key in ('emailAddressList',)) and 'emailAddress' in data['emailAddressList']:
            self.addresses = data['emailAddressList']['emailAddress']

        else:
            raise

    def add_address(self: Alias, address: str) -> None:
        if address not in self.addresses:
            self.addresses.append(address)

    def diff(self: Alias, other_alias: Alias) -> dict:
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

    def replace(self, *pargs, **kwargs) -> bool:
        return self.add(replace=True, *pargs, **kwargs)

    def add(self: Alias, replace: bool = False, *pargs: list, **kwargs: dict) -> bool:
        path = f'{self.api._alias_path(self.name)}'

        data = {'aliasEmails': ','.join(self.addresses)}

        func = self.api.put if replace else self.api.post
        xxx = 'REPLACE' if replace else 'ADD'

        print(f"\n{path}\n   ALIAS {xxx}: {{'{self.name}' => {self.addresses}}}")
        ### response = func(path, data, *pargs, **kwargs)
        ### return self.api._success(response)

    def remove(self: Alias, *pargs: list, **kwargs: dict) -> bool:
        path = f'{self.api._alias_path(self.name)}'

        func = self.api.delete

        print(f"\n{path}\n   ALIAS REMOVE: '{self.name}'")
        ### response = func(path, *pargs, **kwargs)
        ### return self.api._success(response)

    def update(self: Alias, address: str, add: bool =False, remove: bool = False, *pargs: list, **kwargs: dict) -> bool:
        path = f'{self.api._alias_path(self.name)}/{address}'

        if add:
            func = self.api.post
            xxx = f'add: {address}'
        elif remove:
            func = self.api.delete
            xxx = 'remove: {address}'

        print(f"\n{path}\n   ALIAS UPDATE: {self.name} => {xxx}")
        ### response = func(path, data={}, *pargs, **kwargs)
        ### return self.api._success(response)
