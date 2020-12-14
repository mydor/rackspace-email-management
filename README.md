# rackspace-email-management

This is a personal project, designed to allow me to manage my
Rackspace Email service using a simple yaml configuration file.

As I have some 600 email addresses, mostly aliases, trying to
use their web interface would be too time consuming.  The code
herein is designed to make use of their API to manage everything,
in a CaC (Configuration as Code).  I can simply edit the simple
YAML file and run the sync.

## Issues
1. The Rackspace API has rate limits on the API requests.
  * They return 403 Forbidden for exceeding the rate limit, instead
    of the standard 429 Too Many Requests
2. JSON config you receive in a GET request is almost never the format
   required for the PUT/POST requests
  * Data received is often in a tiered data structure, but data sent
    to the API is almost always a flat key/value dictionary.
  * Most of the keys in the GET have to be renamed when flattening the 
    configuration data
  * Some of the keys are mutually exclusive to other keys, EVEN IF the
    API returns them all in the GET.  You have to remove conflicting 
    keys based on the context of the data.

## Requirements
* Python 3.8+

## Setup
* This is designed to run in a python virtual environment "venv"
* Install required python packages

I've simplified the setup process with a `setup.sh` script.  This will
setup the python venv and install the packages from `requirements.txt`.

The best way to run the script is to source it.  You can execute it, but
you then have to activate the python venv yourself after setup.

Source setup.sh
```shell
$ source setup.sh [--prompt <alternate prompt designation>] [--dir <venv directory>]
(env) $
```

Execute setup.sh
```shell
$ ./setup.sh [--prompt <alternate prompt designation>] [--dir <venv directory>]

You must now run `source "env/bin/activate"`

$ source "env/bin/activate"
(env) $
```

**NOTE** If not specified, the directory will be `env` and the prompt prefix
will be `(env)`.

