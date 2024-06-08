# IBKR-Trade-API

This is a simple web server (FastAPI) that can send you a Line message when your IBKR account has a new trading action from your TradingView strategy through webhook.


You can check the functionality from http://localhost:8000/docs after running the server.

## Quick Start

Insert you [Line Notify token](https://notify-bot.line.me/) in `deploy.env` file.

```bash
docker compose up -d
```

You can use `nginx` and `certbot` (requires some backend knowledge) to point https://localhost:5000 and http://localhost:8000 to your own domain (remember to change environment variables in `deploy.env`).

There are some notes taken myself from try-and-error

```bash
# Install dependencies
sudo apt update
sudo apt install certbot python3-certbot-nginx nginx -y

# Get SSL certificates
sudo certbot --nginx -d <YOUR_DOMAIN_FOR_WEBHOOK>
sudo certbot --nginx -d <YOUR_DOMAIN_FOR_CLIENT_PORTAL_API>
```

You can use the following `nginx` configurations to redirect HTTP traffic to HTTPS for all subdomains.
Place it in `/etc/nginx/sites-available/` and create a symbolic link in `/etc/nginx/sites-enabled/`.

```nginx
# Redirect HTTP traffic to HTTPS for all subdomains
server {
    listen 80;
    server_name <YOUR_DOMAIN_FOR_CLIENT_PORTAL_API> <YOUR_DOMAIN_FOR_WEBHOOK>;

    if ($host = <YOUR_DOMAIN_FOR_CLIENT_PORTAL_API>) {
        return 301 https://$host$request_uri;
    }

    if ($host = <YOUR_DOMAIN_FOR_WEBHOOK>) {
        return 301 https://$host$request_uri;
    }
    
    return 301 https://$host$request_uri;
}

# Server configuration for <YOUR_DOMAIN_FOR_CLIENT_PORTAL_API>
server {
    listen 443 ssl http2;
    server_name <YOUR_DOMAIN_FOR_CLIENT_PORTAL_API>;
    ssl_certificate /etc/letsencrypt/live/<YOUR_DOMAIN_FOR_CLIENT_PORTAL_API>/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/<YOUR_DOMAIN_FOR_CLIENT_PORTAL_API>/privkey.pem; # managed by Certbot

    # Recommended SSL optimizations
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass https://localhost:5000;
        include /etc/nginx/proxy_params;  # Includes common proxy settings
    }
}

# Server configuration for <YOUR_DOMAIN_FOR_WEBHOOK>
server {
    listen 443 ssl http2;
    server_name <YOUR_DOMAIN_FOR_WEBHOOK>;
    ssl_certificate /etc/letsencrypt/live/<YOUR_DOMAIN_FOR_WEBHOOK>/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/<YOUR_DOMAIN_FOR_WEBHOOK>/privkey.pem; # managed by Certbot

    # Recommended SSL optimizations
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://localhost:8000;
        include /etc/nginx/proxy_params;  # Includes common proxy settings
    }
}
```

## Cron Job

IBKR Session will expire in few minutes and then you will need to re-login. 

You can schedule a  `cron` task to keep your session alive. 

It is noted that you still need to re-login manually every day, under the current implementation and the limitation of IBKR API.

```bash
# Insert the following line in your crontab, e.g. `crontab -e`
* * * * * /bin/sh /path/to/ibkr-trade-api/runtime.sh

```

It is recommended to schedule the task at the host machine, not in the container.