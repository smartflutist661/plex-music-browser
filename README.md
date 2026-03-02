# readerware-browser

A web interface for browsing a Readerware library built on a PostgreSQL backend.
Using an external DB requires client-server version of Readerware; tested with Readerware 4.31.

## Configuration

Place the database name, username, and password in `.env` in the top level of this repository:

```
DB_NAME=<name>
DB_USERNAME=<username>
DB_PASSWORD=<password>
```

You may also configure `DB_HOST` and `DB_PORT`. They default to `localhost` and `5432`.

It's a [WSGI](https://wsgi.readthedocs.io/en/latest/what.html) application, host in your preferred manner.
An example configuration for WAN access using Apache is provided.

### Example WSGI Config

Install the [Apache2 webserver](https://httpd.apache.org/download.cgi), if you don't already have one.

Install the application requirements in a Python virtual environment (you _can_ use the system environment, but it's not recommended).
`uv` is recommended, e.g. from your home directory:

```bash
pip install uv
uv venv
uv pip install -r <path/to/repo>/pyproject.toml
```

Place a `wsgi-file` with the following contents in a folder the Apache daemon has access to, e.g. `/var/www/html`:

```
import sys

sys.path.insert(0, '</absolute/path/to/this/repo>/readerware-browser')
sys.path.insert(0, '</absolute/path/to/python/site-packages>')

from readerware_browser import APP as application
```

Enable the Apache WSGI module: `a2enmod wsgi`

Create a `readerware.conf` file in `/etc/apache2/sites-available/` with contents like:

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
You may need to add `WEBROOT=<your-webroot>` to the `.env` file (default `/var/www/html`);
then set up and enable a LetsEncrypt SSL certificate using [certbot](https://certbot.eff.org/instructions?ws=apache&os=snap) for your server domain.

Enable the site: `a2ensite readerware`

Then restart the Apache2 service: `service apache2 restart`
