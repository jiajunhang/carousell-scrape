# Carousell Scraper
This is a scraper written for Carousell.

It is able to fetch listings from carousell based on your queries and send updates to Telegram via your own Telegram bot.

## How to use

1. Setup a Telegram bot using BotFather. Note the unique generated bot token.
2. Send a message to your bot and retrieve the chat ID via the following endpoint: `https://api.telegram.org/bot{bot_token}/getUpdates`
3. Run the script `python app.py`
4. Fill in inputs as described

## Input required
1. `bot_token` -- unique token for your own Telegram bot
2. `chat_id` -- unique ID for your chat with the Telegram bot
3. `search window time` -- window for the posted time of your listings (i.e. within last 1hr == 3600 seconds)
4. `alert rate` -- how often to send updates to Telegram chat
5. `queries` -- accepts a list of comma-separated queries

## Example

```
python app.py
Enter bot token>123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
Enter chat id>1234567
Enter search window time>3600
Enter alert rate>3600
Enter queries>ps4,ps4 slim,ps4 games
```