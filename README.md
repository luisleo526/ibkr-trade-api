# IBKR-Trade-API

This is a simple web server (FastAPI) that can send you a Line message when your IBKR account has a new trading action from your TradingView strategy through webhook.


You can check the functionality from http://localhost:8000/docs after running the server.

## Quick Start

Insert you [Line Notify token](https://notify-bot.line.me/) in `deploy.env` file.

```bash
docker compose up -d
```

You can use `nginx` and `certbot` (requires some backend knowledge) to point https://localhost:5000 and http://localhost:8000 to your own domain (remember to change environment variables in `deploy.env`).

## Cron Job

IBKR Session will expire in few minutes and then you will need to re-login. 

You can schedule a  `cron` task to keep your session alive. 

It is noted that you still need to re-login manually every day, under the current implementation and the limitation of IBKR API.

```bash
# Insert the following line in your crontab, e.g. `crontab -e`
* * * * * /bin/sh /path/to/ibkr-trade-api/runtime.sh

```

It is recommended to schedule the task at the host machine, not in the container.