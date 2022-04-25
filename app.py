import requests
import json
import time
import os

from datetime import datetime as dt
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram.ext import Updater, InlineQueryHandler, CommandHandler

load_dotenv()

CAROUSELL_API = os.environ['CAROUSELL_API']
BOT_TOKEN = os.environ['BOT_TOKEN']

class Item:
    def __init__(self, keyword, user, time, title, price, desc, condition):
        self.keyword = keyword
        self.user = user
        self.time = time
        self.title = title
        self.price = price
        self.desc = desc
        self.condition = condition
    
    def toJSON(self):
        return json.dumps(self, default=lambda o:o.__dict__, sort_keys=True, indent=4)

"""
V1 Method
Scrape via DOM elements, do not use
"""
def fetch_page():

    printTime()
    # GET Request
    r = requests.get('https://www.carousell.sg/search/ps4%20slim?addRecent=true&canChangeKeyword=true&includeSuggestions=true&searchId=C2rvQR')
    #print(r.status_code)
    
    # Init bs4 object
    soup = BeautifulSoup(r.text, 'lxml')
   
    # Fetch all 'div' elements
    # due to dynamic css, unable to use regular css selector
    allDiv = soup.find_all("div")
    #print(len(allDiv) )

    # Extracting all listing elements
    listing_divs = []

    for d in allDiv:
        if "data-testid" in d.attrs:
            listing_divs.append(d)
    
    print("No. of listigns detected: ", len(listing_divs))


    # Iterate over each list element & extract
    # i) Time since post
    # ii) Username
    # iii) Title of listing
    # iv) Price
    # v) Condition

    for listing in listing_divs:

        top_chunk = listing.contents[0]
        
        name_time_anchor = top_chunk.contents[0]
        content_anchor = top_chunk.contents[1]

        name_time_wrapper = name_time_anchor.contents[1]
        name = name_time_wrapper.contents[0].text

        time_wrapper = name_time_wrapper.contents[1]
        time = time_wrapper.contents[0].text
        
        title = content_anchor.contents[1].contents[0]
        price = content_anchor.contents[2].text
        condition = content_anchor.contents[4].text

        i = Item(name, time, title, price, condition)

        if isNewItem(i):
            update(i)

def isNewItem(item):
    if "minutes" in item.time:
        tokens = item.time.split(" ")
        if int(tokens[0]) <= 2:
            print(item)
            return True
    
    return False

""" def update(item):
    url = TELEGRAM_API + item.toJSON()
    requests.get(url) """

def printTime():
    t = time.localtime()
    current_time = time.strftime("%d/%m - %H:%M:%S", t)


"""
Fetch carousell queries based on API
"""
def fetch_api(queries, within):
    result = []
    item_set = set()

    for query in queries:
        payload = construct_payload(query)
        r = requests.post(CAROUSELL_API, data = payload)
        res = r.json()

        listings = res["data"]["results"]

        for listing in listings:
            item = parse_result(query, listing)
            if is_new_item_unix(item, within):
                item_meta = item.user + item.title + str(item.time)
                if item_meta not in item_set:
                    item_set.add(item_meta)
                    result.append(item)
    
    result.sort(key=lambda x: x.time, reverse=True)
    return list(set(result))

"""
Convert listing object into JSON
"""
def parse_result(keyword, item):
    username = item["listingCard"]["seller"]["username"]
    timestamp = 0
    title = item["listingCard"]["title"]
    price = item["listingCard"]["price"]
    desc = item["listingCard"]["belowFold"][2]["stringContent"]
    condition = item["listingCard"]["belowFold"][3]["stringContent"]

    if "timestampContent" in item["listingCard"]["aboveFold"][0]:
        timestamp = item["listingCard"]["aboveFold"][0]["timestampContent"]["seconds"]["low"]

    i = Item(keyword, username, timestamp, title, price, desc, condition)
    return i

"""
Check listing item created time
"""
def is_new_item_unix(item, within):
    currTime = time.time()
    itemTime = item.time

    diff = currTime - itemTime

    if diff < within:
        return True
    
    return False

"""
Hardcoded request payload
"""
def construct_payload(query):
    body = {
        "bestMatchEnabled": True,
        "canChangeKeyword": True,
        "ccid": "5727",
        "count": 20,
        "countryCode": "SG",
        "countryId": "1880251",
        "filters": [],
        "includeEducationBanner": True,
        "includeSuggestions": False,
        "locale": "en",
        "prefill": {
            "prefill_sort_by": "3"
        },
        "query": query,
        "sortParam": {
            "fieldName": "3"
        }
    }
    return body

def format_message(results):
    output = ""
    #output = output + time.strftime("%d/%m/%Y, %I:%M:%S%p", time.localtime())
    #output += "\n"

    for res in results:
        entry = res.keyword + " | " + res.user + " | " + res.title + " | " + res.price + " | " + format_date(res.time) + "\n"
        output = output + entry + "\n"
    
    return output

def format_date(ts):
    itemdate = dt.fromtimestamp(ts)
    return itemdate.strftime("%d/%m/%Y, %I:%M:%S%p")

def pull_cmd(update, context):
    args = " ".join(context.args)
    queries = args.split(',')

    for query in queries:
        update.message.reply_text("Querying for: " + query)

    results = fetch_api(queries, 3600)
    if len(results) > 0:
        msg = format_message(results)
        update.message.reply_text(msg)
    else:
        update.message.reply_text("No results within last 1hr.")

def help_cmd(update, context):
    update.message.reply_text("Use the /pull command to extract entries that were uploaded in the last 1hr using a comma-separated query. E.g. /pull ps4, ps4 slim")

def settings_cmd(update,context):
    window = context.user_data.get('post_window', int("3600"))
    update_interval = context.user_data.get('update_interval', int("3600"))
    queries = context.user_data.get('queries', [])

    settings = {
        "post_window": str(window) + " seconds",
        "update_interval": str(update_interval) + " seconds",
        "queries": queries
    }

    update.message.reply_text(json.dumps(settings))

def set_window_cmd(update, context):
    try:
        value = int(update.message.text.partition(' ')[2])
        
        if (value < 300 or value > 86400):
            update.message.reply_text("Please input a value between 300 (5 minutes) to 86400 (1 day).")
        else:
            context.user_data['post_window'] = value
            update.message.reply_text("All listings posted in the last: {} seconds will be fetched.".format(value))
    except:
        update.message.reply_text("Invalid input. Please only input a value between 300 (5 minutes) to 86400 (1 day).")
    
def set_update_interval_cmd(update, context):
    try:
        value = int(update.message.text.partition(' ')[2])
        
        if (value < 60 or value > 86400):
            update.message.reply_text("Please input a value between 300 (5 minutes) to 86400 (1 day).")
        else:
            context.user_data['update_interval'] = value
            update.message.reply_text("Update notifications will be sent every: {} seconds.".format(value))
    except:
        update.message.reply_text("Invalid input. Please only input a value between 300 (5 minutes) to 86400 (1 day).")

def set_query_cmd(update, context):
    try:
        value = update.message.text.partition(' ')[2]
        if len(value) == 0:
            update.message.reply_text("Invalid input, please key in at least one search term.")
        else:
            queries = value.split(",")
            if len(queries) > 5:
                queries = queries[:5]
                update.message.reply_text("More than 5 search terms detected, only first 5 will be registered.")
            context.user_data["queries"] = queries
            update.message.reply_text("Queries registered: {}".format(queries))
    except:
        update.message.reply_text("Invalid input.")


def start_cmd(update, context):
    print("Start cmd called by user: {}".format(update.message.chat_id))

    chat_id = update.message.chat_id
    queries = context.user_data['queries']
    window = context.user_data.get('post_window') if context.user_data.get('post_window') else 3600
    interval = context.user_data.get('update_interval') if context.user_data.get('update_interval') else 3600

    ctx = {
        "chat_id": chat_id,
        "queries": queries,
        "post_window": window
    }

    currJob = context.job_queue.run_repeating(fetch_callback, interval=interval, first=10, name=str(chat_id), context=ctx)
    
    context.user_data['job'] = currJob

def stop_cmd(update, context):
    job = context.user_data['job']
    job.schedule_removal()

    update.message.reply_text("Stopped fetching.")

def fetch_callback(context):
    print("[fetch_callback]")
    chat_id = context.job.context['chat_id']
    queries = context.job.context['queries']
    window = context.job.context['post_window']

    print("[fetch_callback] chat_id={}".format(chat_id))
    print("[fetch_callback] len(queries)={}".format(str(len(queries))))
    print("[fetch_callback] window={}".format(str(window)))

    res = fetch_api(queries, window)
    if len(res) > 0:
        msg = format_message(res)
        context.bot.send_message(chat_id, text=msg)
    else:
        context.bot.send_message(chat_id, text=("No results within last {} seconds.".format(window)))



def main():
    updater = Updater(BOT_TOKEN, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler('help', help_cmd))
    
    dp.add_handler(CommandHandler('settings', settings_cmd))

    dp.add_handler(CommandHandler('setwindow', set_window_cmd))
    dp.add_handler(CommandHandler('setinterval', set_update_interval_cmd))
    dp.add_handler(CommandHandler('setquery', set_query_cmd))

    dp.add_handler(CommandHandler('start', start_cmd))
    dp.add_handler(CommandHandler('stop', stop_cmd))

    #dp.add_handler(CommandHandler('pull', pull_cmd))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
