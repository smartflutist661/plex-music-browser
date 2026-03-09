# plex-music-browser

A web interface for browsing some basic music metadata from a Plex SQLite database, mostly for visualization purposes.
Tested with Plex Server version 1.43.0.10492.

## Configuration

Copy the Plex database file to your webroot. Place the database filename and numeric ID of the library you want to browse in `.env` in the top level of this repository:

```
DB_FILE=</full/path/to/file>
LIBRARY_ID=<libraryID>
```

If you want a permanent installation to update regularly, one option is setting up a cron job to copy the database file as often as you want to refresh the data.

It's a [WSGI](https://wsgi.readthedocs.io/en/latest/what.html) application, host in your preferred manner.
An example configuration for WAN access using Apache is provided.

### Example WSGI Config

Install the [Apache2 webserver](https://httpd.apache.org/download.cgi), if you don't already have one.

Install the application requirements in a Python virtual environment (you _can_ use the system environment, but it's not recommended).
`uv` is recommended, e.g. from the repository:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

Place a `wsgi-file` with the following contents in a folder the Apache daemon has access to, e.g. `/var/www/html`:

```
import sys

sys.path.insert(0, '</absolute/path/to/this/repo>/plex-music-browser')
sys.path.insert(0, '</absolute/path/to/python/site-packages>')

from plex_music_browser import APP as application
```

Enable the Apache WSGI module: `a2enmod wsgi`

Create a configuration file in `/etc/apache2/sites-available/` with contents like:

```
<VirtualHost *:80>
        ServerName <your-server-domain>
        Redirect permanent / https://<your-server-domain>/
</VirtualHost>

<VirtualHost *:443>
        WSGIScriptAlias / <your-webroot>/<wsgi-file>
        ServerName <your-server-domain>

        SSLEngine On

        <Directory <your-webroot>>
                Require all granted
                Options +IncludesNOEXEC
        </Directory>

        Include /etc/letsencrypt/options-ssl-apache.conf
        SSLCertificateFile /etc/letsencrypt/live/<your-server-domain>/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/<your-server-domain>/privkey.pem

        ErrorLog ${APACHE_LOG_DIR}/error.log
        CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```

This configuration assumes you want to enable SSL and prevent plain HTTP connections.
This application supports webroot-based ACME HTTP01 challenges if you're unable to complete any other types of challenge.
You may need to add `WEBROOT=<your-webroot>` to the `.env` file (default `/var/www/html`);
then set up and enable a LetsEncrypt SSL certificate using [certbot](https://certbot.eff.org/instructions?ws=apache&os=snap) for your server domain.

Enable the site: `a2ensite <conf-name>`

Then restart the Apache2 service: `service apache2 restart`
