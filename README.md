# Carousell Scraper
This is a scraper-turned-Telegram-bot written for Carousell.

It is able to fetch listings from carousell based on your queries.

## How to use

1. Start a chat with @carousell_scraper_bot
2. Use `/help` command for instructions.
3. Use `/pull` command to extract entries that were posted within last 1h.

## Example
```
/pull ps4, ps4 slim
```

## Future Work
* Define timeframe/window for listings (i.e. last X hours / minutes)
* Repeating jobs (e.g. based on queries, send an update every 30 minutes)
* Rate-limiting for obvious reasons