#!/bin/env python3

from rackspace import Api
from rackspace import Aliases
from rackspace import Accounts
import yaml
import json

with open('cfg.yml', 'r') as fh:
    raw = fh.read()
CONFIG = yaml.safe_load(raw)

api = Api(CONFIG['user_key'], CONFIG['secret_key'])

aliases = Aliases(api)
accounts = Accounts(api)

api.customer = CONFIG['customer_id']
api.domain = 'arch-mage.com'
api.domain = 'moonlightimagery.com'

def status(response, status_code=None):
    if status_code is None:
        status_code = 200

    print(response.status_code)
    if response.text:
        print(json.dumps(response.json(), sort_keys=True, indent=4))
    assert response.status_code == status_code

data = accounts.get_accounts()
test = data['testremove']
print(test)
test.remove()

### #api.httpclient_logging_patch()
### response = accounts.get_accounts()
### status(response)
### 
### #api.httpclient_logging_unpatch()
### response = accounts.get_account('junk')
### status(response)

### response = accounts.add_account('hobbies', data={
###     'password': 'Calic0%2',
###     'size': 25600,
###     'lastName': 'Smith',
###     'firstName': 'Michael',
###     'displayName': 'Michael Smith',
###     'enabled': True,
###     'visibleInRackspaceEmailCompanyDirectory': True,
###     'notes': 'Managed by sync script',
### })
### status(response)

### response = accounts.update_account('hobbies', data={
###     'initials': 'G'
### })
### status(response)

### response = accounts.get_account('hobbies')
### status(response)

### response = accounts.rename_account('hobbies', 'hobbies-remove')
### status(response)

### response = accounts.del_account('hobbies')
### status(response)
