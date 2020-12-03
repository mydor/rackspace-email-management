from __future__ import annotations

class Spam(object):
    def __init__(self: Spam, domain, data: dict =None, api=None, account=None) -> None:
        self.domain = domain
        self.account = account

        if api is not None:
            self.api = api

        for k,f,kwargs in ( ('settings', self.load_settings, {}), ### Config load
                            ('rsEmailSettings', self.load_settings, {'update': True}), ### RackSpace data set
                            ('blocklist', self.load_blocklist, {}), ('ipblocklist', self.load_ipblocklist, {}),
                            ('safelist', self.load_safelist, {}), ('ipsafelist', self.load_ipsafelist, {}),):
            f(data.get(k) if data else None, **kwargs)

        # RackSpace data set has the filterLevel outside the settings structure
        # so, catch and handle it here
        if 'filterLevel' in data:
            self.settings['filterLevel'] = data['filterLevel']

    def load_settings(self: Spam, settings: dict =None, update=False) -> None:
        if getattr(self, 'settings', None) is None:
            self.settings = {}

        if not isinstance(settings, dict):
            return

        if not update:
            self.settings = settings

        else:
            for k,v in settings.items():
                self.settings.update({k:v})

    def load_blocklist(self: Spam, blocklist: list =None) -> None:
        if getattr(self, 'blocklist', None) is None:
            self.blocklist = []

        if isinstance(blocklist, list):
            self.blocklist = blocklist

    def load_ipblocklist(self: Spam, ipblocklist: list =None) -> None:
        if getattr(self, 'ipblocklist', None) is None:
            self.ipblocklist = []

        if isinstance(ipblocklist, list):
            self.ipblocklist = ipblocklist

    def load_safelist(self: Spam, safelist: list =None) -> None:
        if getattr(self, 'safelist', None) is None:
            self.safelist = []

        if isinstance(safelist, list):
            self.safelist = safelist

    def load_ipsafelist(self: Spam, ipsafelist: list =None) -> None:
        if getattr(self, 'ipsafelist', None) is None:
            self.ipsafelist = []

        if isinstance(ipsafelist, list):
            self.ipsafelist = ipsafelist

    def 
### GET /customers/12345678/domains/example.com/spam/settings
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
###   - "bounce-350_HTML-13278537-136453-515003010-744@bounce.email.bayphoto.com"
###   - "bounce-350_HTML-13278537-137710-515003010-744@bounce.email.bayphoto.com"
###   - "bounce-350_HTML-13278537-138783-515003010-744@bounce.email.bayphoto.com"
###   - "bounce-350_HTML-13278537-147881-515003010-744@bounce.email.bayphoto.com"
###   - "bounce-351_HTML-13278537-135299-515003010-744@bounce.email.bayphoto.com"
### ipsafelist: []
