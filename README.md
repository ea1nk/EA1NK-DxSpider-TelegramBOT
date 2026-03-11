```
███████╗ ██████╗ ██████╗     ██████╗ ███████╗██╗   ██╗██╗ ██████╗███████╗███████╗
██╔════╝██╔════╝██╔═══██╗    ██╔══██╗██╔════╝██║   ██║██║██╔════╝██╔════╝██╔════╝
███████╗██║     ██║   ██║    ██║  ██║█████╗  ██║   ██║██║██║     █████╗  ███████╗
╚════██║██║     ██║▄▄ ██║    ██║  ██║██╔══╝  ╚██╗ ██╔╝██║██║     ██╔══╝  ╚════██║
███████║╚██████╗╚██████╔╝    ██████╔╝███████╗ ╚████╔╝ ██║╚██████╗███████╗███████║
╚══════╝ ╚═════╝ ╚══▀▀═╝     ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝╚══════╝
                                                                                 
███████╗ █████╗  ██╗███╗   ██╗██╗  ██╗                                           
██╔════╝██╔══██╗███║████╗  ██║██║ ██╔╝                                           
█████╗  ███████║╚██║██╔██╗ ██║█████╔╝                                            
██╔══╝  ██╔══██║ ██║██║╚██╗██║██╔═██╗                                            
███████╗██║  ██║ ██║██║ ╚████║██║  ██╗           
2026 EA1NK-DxSpider-TelegramBOT
```
# :robot: EA1NK-DxSpider-TelegramBOT

Telegram bot for DX alerts from a DXSpider cluster, with user filters, duplicate suppression, and optional RBN filtering.

This repository is designed to run in Docker and is part of the EA1NK-Docker-DxSpider project:
https://github.com/ea1nk/EA1NK-Docker-DxSpider

## What it does

- Connects to a DXSpider node via telnet.
- Parses incoming DX spots in real time.
- Sends Telegram alerts only to users interested in the spotted call, band, and mode.
- Stores per-user filters in local SQLite storage.
- Optionally excludes RBN/Skimmer spots per user.
- Can query recent spots from a MySQL cluster database for the /last command.

## Project structure

- main.py: Telegram bot runtime and command handlers.
- database.py: SQLite filter store and MySQL spot lookup.
- logic.py: Band detection and mode inference.
- localestr.py: Localized bot messages.
- Dockerfile: Container image definition.
- docker-compose.yml.sample: Example service configuration.

## Requirements

- Python 3.10+
- A Telegram bot token from BotFather.
- Access to a DXSpider host and port.
- Optional: MySQL access to the cluster spots database (required for /last).

## Quick BotFather guides

- English: [HOW_TO_TELEGRAM_BOT_EN,md](HOW_TO_TELEGRAM_BOT_EN,md)
- Espanol: [TELEGRAM_BOT_COMO.md](TELEGRAM_BOT_COMO.md)

Python dependencies are listed in requirements.txt:

- python-telegram-bot==21.0.1
- mysql-connector-python==8.3.0

## Environment variables

Required:

- BOT_TOKEN: Telegram bot token.

Recommended:

- SPIDER_HOST: DXSpider hostname (default: dxspider).
- SPIDER_PORT: DXSpider port (default: 23).
- MY_CALL: Callsign used to log in to the cluster (default: BOT).

For /last command (MySQL spots DB):

- CLUSTER_DB_HOST: MySQL host (default in code: dxspider-db).
- CLUSTER_DB_NAME: Database name.
- CLUSTER_DB_USER: Database user.
- CLUSTER_DB_PASS: Database password.

Optional proxy variables:

- HTTP_PROXY
- HTTPS_PROXY
- http_proxy
- https_proxy
- NO_PROXY

## Local run (without Docker)

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Export environment variables:

```bash
export BOT_TOKEN="your_telegram_token"
export SPIDER_HOST="dxspider"
export SPIDER_PORT="23"
export MY_CALL="YOURCALL"

# Optional, only for /last
export CLUSTER_DB_HOST="spider_database"
export CLUSTER_DB_NAME="your_db"
export CLUSTER_DB_USER="your_user"
export CLUSTER_DB_PASS="your_password"
```

3. Run:

```bash
python main.py
```

## Docker Compose run

This is the recommended deployment mode for this bot.

1. Create your compose file from the sample:

```bash
cp docker-compose.yml.sample docker-compose.yml
```

2. Edit values in docker-compose.yml, especially:

- BOT_TOKEN
- MY_CALL
- CLUSTER_DB_NAME
- CLUSTER_DB_USER
- CLUSTER_DB_PASS

3. Start service:

```bash
docker compose up -d --build
```

4. Check logs:

```bash
docker compose logs -f dx-telegram-bot
```

## Telegram commands

- /start
- /help
- /setfilter [CALL] [BANDS] [MODE]
- /myfilters
- /delfilter [ID]
- /last [CALL]
- /rbn on|off

## Data persistence

- SQLite file is stored in /app/data inside the container.
- In compose sample, this is mapped from ./bot_data on host.

## Notes

- If the bot cannot reach DXSpider, it retries automatically.
- Duplicate alerts are suppressed for 10 minutes.
