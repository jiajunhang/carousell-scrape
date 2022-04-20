import requests
import json
import time
import os

from datetime import datetime as dt
from dotenv import load_dotenv
from bs4 import BeautifulSoup

CAROUSELL_API = os.environ["CAROUSELL_API"]

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

def update(item):
    url = TELEGRAM_API + item.toJSON()
    requests.get(url)

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
    output = output + time.strftime("%d/%m/%Y, %I:%M:%S%p", time.localtime())
    output += "\n"

    for res in results:
        entry = res.keyword + " | " + res.user + " | " + res.title + " | " + res.price + " | " + format_date(res.time) + "\n"
        output = output + entry + "\n"
    
    return output

def format_date(ts):
    itemdate = dt.fromtimestamp(ts)
    return itemdate.strftime("%d/%m/%Y, %I:%M:%S%p")


def main():
    bot_token = input("Enter bot token>")
    chat_id = input("Enter chat id>")
    within_time = int(input("Enter search window time (i.e. item posted within last X seconds)>"))
    alert_rate = int(input("Enter alert rate (i.e. how often to send updates to chat, in seconds)>"))
    queryString = input("Enter queries (if multiple, comma-separated)>")

    tele_api = "https://api.telegram.org/bot{}/sendMessage?chat_id={}&text=".format(bot_token, chat_id)

    queries = queryString.split(',')

    print("Search window: " + str(within_time) + "s")
    print("Alert every: " + str(alert_rate) + "s")
    print("Queries: ")
    print('\n'.join(map(str,queries)))

    while True:
        results = fetch_api(queries, within_time)

        if len(results) > 0:
            msg = format_message(results)
            print(msg)
            url = tele_api + msg
            requests.get(url)
        time.sleep(alert_rate)

if __name__ == "__main__":
    main()
