#!/bin/env python3

from rackspace import Api
from rackspace import Aliases
import yaml
import json

with open('cfg.yml', 'r') as fh:
    raw = fh.read()
CONFIG = yaml.safe_load(raw)

api = Api(CONFIG['user_key'], CONFIG['secret_key'])
aliases = Aliases(api)

api.customer = CONFIG['customer_id']
api.domain = 'arch-mage.com'

def status(response, status_code=None):
    if status_code is None:
        status_code = 200

    print(response.status_code)
    assert response.status_code == status_code
    if response.text:
        print(json.dumps(response.json(), sort_keys=True, indent=4))

def check(alias=None, status_code=None):
    if alias is None:
        alias = 'testremove'

    response = aliases.get_alias(alias)
    status(response, status_code)

data = aliases.get_aliases()
print(data)
### response = aliases.get_aliases()
### status(response)
### 
### check('testtest')
### check('avantgo')

### print("Add testremove -> archmage-tn")
### response = aliases.add_alias('testremove', targets=['archmage-tn@arch-mage.com'])
### status(response)
### 
### check('testremove')
### 
### print("Force testremove -> junk")
### response = aliases.add_alias('testremove', targets=['junk@arch-mage.com'], _set=True)
### status(response)
### 
### check('testremove')
### 
### print("FAIL: Add testremove -> archmage-tn")
### response = aliases.add_alias('testremove', targets=['archmage-tn@arch-mage.com'])
### status(response, 400)
### 
### check('testremove')
### 
### print("Add archmage-tn to testremove")
### response = aliases.update_alias('testremove', 'archmage-tn@arch-mage.com', add=True)
### status(response)
### 
### check('testremove')
### 
### print("Remove junk from testremove")
### response = aliases.update_alias('testremove', 'junk@arch-mage.com', remove=True)
### status(response)
### 
### check('testremove')
### 
### print("Remove testremove")
### response = aliases.del_alias('testremove')
### status(response)
### 
### check('testremove', 404)
### 
