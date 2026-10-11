# Phone Deal Alert Bot

## Running on Replit

- Keep the existing Python 3.12 stack and `bot.py` entry point.
- Dependencies are listed in `requirements.txt`.
- Add `BOT_TOKEN` through Replit Secrets. Get the token from Telegram's official `@BotFather`; never paste it into chat or commit it.
- Click Run to start the `Telegram deal bot` workflow (`PORT=8000 python bot.py`).
- The bot uses Telegram polling. Stop any other instance using the same token to avoid polling conflicts.
- Open the bot in Telegram and send `/start`. Available commands: `/settings`, `/discount 70`, `/drop 25`, `/maxprice 20000`, and `/scan`.
- Scans run every 30 minutes by default; optional `SCAN_MINUTES` changes that interval.
- The existing HTTP health endpoint listens on `0.0.0.0:8000` in the workflow. It is not a web dashboard and does not verify successful Telegram authentication.
- User settings and tracked products are stored in local `deals.db`; do not commit the database.

## External services

Telegram requires a valid `BOT_TOKEN` before startup. Amazon and Flipkart can block automated requests or change their page markup, so a running bot does not guarantee that scans return products.
The existing code supports an optional `SCRAPER_KEY`; it is not required for startup and has not been configured.
