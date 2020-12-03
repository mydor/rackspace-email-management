from rackspace import Account
from rackspace import Accounts
from rackspace import Aliases
from rackspace import Api
import json
import yaml

### json_data = json.loads(""" { "contactInfo": { "businessCity": "", "businessCountry": "", "businessNumber": null, "businessPostalCode": "", "businessState": "", "businessStreet": "", "customID": null, "employeeType": null, "faxNumber": null, "firstName": "Michael", "generationQualifier": null, "homeCity": "", "homeCountry": "", "homeFaxNumber": null, "homeNumber": null, "homePostalCode": "", "homeState": "", "homeStreet": "", "initials": "G", "lastName": "Smith", "mobileNumber": null, "notes": "Managed by sync script", "organizationUnit": null, "organizationalStatus": null, "pagerNumber": null, "title": null, "userID": null }, "createdDate": "11/23/2020 12:34:25 PM", "currentUsage": 0, "displayName": "Michael Smith", "emailForwardingAddressList": [], "enableVacationMessage": false, "enabled": true, "lastLogin": "", "name": "hobbies", "saveForwardedEmail": false, "size": 25600, "vacationMessage": "", "visibleInExchangeGAL": false, "visibleInRackspaceEmailCompanyDirectory": true } """)
### z = Account(from_json=json_data)
### y = Account(data={'lastName': 'Smith', 'firstName': 'Michael', 'password': 'wizard5', 'displayName': 'Michael Smith', 'enabled': True, 'size': 25600})
### y.diff(z)
### ### {'enableVacationMessage': None, 'vacationMessage': None, 'enableForwardingAddresses': None, 'saveForwardedEmail': None, 'generationQualifier': None, 'initials': None, 'organizationUnit': None, 'businessNumber': None, 'pagerNumber': None, 'homeNumber': None, 'mobileNumber': None, 'faxNumber': None, 'homeFaxNumber': None, 'businessStreet': None, 'businessCity': None, 'businessState': None, 'businessPostalCode': None, 'businessCountry': None, 'homeStreet': None, 'homeCity': None, 'homeState': None, 'homePostalCode': None, 'homeCountry': None, 'notes': None, 'title': None, 'userID': None, 'organizationalStatus': None, 'employeeType': None, 'customID': None, 'visibleInRackspaceEmailCompanyDirectory': None, 'visibleInExchangeGAL': None, 'createdDate': None}


with open('cfg.yml', 'r') as fh:
    raw = fh.read()
CONFIG = yaml.safe_load(raw)

api = Api(CONFIG['user_key'], CONFIG['secret_key'])

aliases = Aliases(api)
accounts = Accounts(api)

api.customer = CONFIG['customer_id']
api.domain = 'arch-mage.com'

with open(f'{api.domain}.yml', 'r') as fh:
    draw = fh.read();
DOMAIN_DATA = yaml.safe_load(draw)

def status(response, status_code=None):
    if status_code is None:
        status_code = 200

    print(response.status_code)
    if response.text:
        print(json.dumps(response.json(), sort_keys=True, indent=4))
    assert response.status_code == status_code

### #api.httpclient_logging_patch()
### response = accounts.get_accounts()
### status(response)
### 
### #api.httpclient_logging_unpatch()

response = accounts.get_account('junk')
status(response)
from_rackspace = Account(response.json())

account = 'junk@arch-mage.com'
from_config = Account(DOMAIN_DATA[account])

diff = from_config.diff(from_rackspace)
if len(diff) > 0:
    print(diff)
    #response = accounts.update_account(account[:account.index('@')], data=diff)
    #status(response)

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
