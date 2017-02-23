# Mango

Mapping Application for NGOs


## Dependencies


### Debian/Ubuntu

    make -f deps.Makefile dev

    # download elasticsearch deb from http://www.elasticsearch.org/download
    sudo dpkg -i elasticsearch-0...

## 3rd party web resources

Read `web/vendor/Makefile` for how to get jQuery-UI.

Then:

    make -C vendor
    
Update Geolocation to make it Python 3 compatible:

    2to3 -w vendor/geolocation.py
    
## Configuration

    make -f mysql.Makefile .mango.conf
    make .xsrf
    
## Database

    make -f mysql.Makefile mysql-import




### Services

#### Google OAuth 2.0

Requires a Google OAuth 2.0 Client ID

Sign in to Google as `caatdata@gmail.com`.

Go to:

https://console.developers.google.com/project

Create/Edit App:

Name: CAAT Mango
ID: caat-data-mango

Go to > APIs & Auth > Credentials > Create new Client ID > Web application

Email address: caatdata@gmail.com
Product Name: CAAT Mapping Application

Authorized JavaScript origins:
    https://www.caat.org.uk
    https://www-dev.caat.org.uk
    http://localhost:8802/

Authorized redirect URIs:
    https://www.caat.org.uk/resources/mapping/auth/login/google
    https://www-dev.caat.org.uk/resources/mapping/auth/login/google
    http://localhost:8802/auth/login/google
    
#### Google Maps API

Go to:

    https://developers.google.com/maps/documentation/javascript/get-api-key#key

Click "Get a key"

Choose project "CAAT Mango"

Copy API key into ".mango.conf"


### 3rd party static content

Download the latest jQuery-UI package from <http://jqueryui.com/download/> to a temporary location. It should include at least the modules:

-   Autocomplete
-   Datepicker
-   Blind Effect
    
Expand to vendor directory
    
    unzip jquery-ui-*.custom.zip -d vendor


### Build

Now make:

    make

And follow any instructions


## Launch

    ./mango.py


### Inserting Organisation JSON

Example:

    ./tools/insert_organisations.py /tmp/dsei-2015.json

MySQL

    select count(*) from org_orgtag join orgtag using (orgtag_id) where base_short = "dsei-2015";

    delete org_orgtag from org_orgtag join orgtag using (orgtag_id) where base_short = "dsei-2015";

    
