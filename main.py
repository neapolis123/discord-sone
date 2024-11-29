
import discord
from discord.ext import commands
from zoneinfo import ZoneInfo
import asyncio
import aiohttp
import requests
import pprint
import datetime
import traceback
import os
import time as t
#https://www.youtube.com/watch?v=9nCiT_Wt3_w&ab_channel=Oliver%27sTech
#https://www.youtube.com/watch?v=UYJDKSah-Ww&ab_channel=Indently

intents = discord.Intents.default()
intents.members=True
intents.message_content = True

bot = commands.Bot(command_prefix='/',intents=intents)

blocked_set = set()


@bot.event
async def on_ready():
    #channel = bot.get_channel(1306738767280738354) good to keep if i decide to change from DMS to channels posting
    me = await bot.fetch_user(253660472803328002)
    start = datetime.time.fromisoformat('05:00:00')
    nyc_close_time = datetime.time.fromisoformat('20:00:00')
    await me.send('Starting\n')
    iteration = 0
    previously_notified_or_discarded = set()
    while (True):
        try:
            nyc_date = datetime.datetime.now(tz=ZoneInfo('America/New_York'))
            nyc_time = nyc_date.time()
            today = nyc_date.weekday()
            if  0 <= today <= 4:  # if weekend just sleep
                if start <= nyc_time <= nyc_close_time: # If 7am and 8pm
                    iteration += 1
                    print(iteration)
                    dict_worth_watching = {}
                    try:  #the previously_notified set here is updated inside play to add IPOs and Reselling Shareholders S-1s, its shared between the inner logic and this outer logic , it is reset at the end of every day
                      dict_worth_watching = await play(previously_notified_or_discarded)  # one dict with all tickers as keys {'UAVS': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=8504&owner=exclude&count=40',price:5},'QUBT': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1758009&owner=exclude&count=40',price:10} }
                    except Exception:                     # this dict has all the tickers that have fillings in the last 30days that include S-1 and F-1, if we reached this point, it means that these tickers will be notified because they were filtered as not preivously notified/discard in 'get_fillings' and if a a ticker has a filling but it's a seller shareholder one it will be added to the discarded without making it to this step
                      await me.send(f'A problem has been encountered in fetching logic: \n```{traceback.format_exc()[-1700:]}``` \nSleeping for 10 mins after failed fetched attempt at {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                      print(f'Problem encountered with the logi \nSleeping for 30 mins after failed fetched attempt at {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                      await asyncio.sleep(60*30)
                      continue
                    print(f'the set to be notified is {set(dict_worth_watching.keys())}') # the set that we got from the logic {'UAVS': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=8504&owner=exclude&count=40',price:5},'QUBT': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1758009&owner=exclude&count=40',price:10} }
                    print(f'notified/discarded set is {previously_notified_or_discarded}') # for ease of debugging in the future
                    if dict_worth_watching:   #If there are tickers to be notified
                        for ticker, info in dict_worth_watching.items():           #this is for formating so that each ticker send on chat is a hyperlink linking to the fillings
                            if info['latest_filling_date'] == str(datetime.datetime.today().date()):
                               await me.send(f'- [{ticker}]({info["link"]}) ${info["price"]} - Has a filling today ') # this checks if it has a filling today, quality of life to avoid opening everyday when something is relevant over multiple days but awaiting an amendment
                            else:
                               await me.send(f'- [{ticker}]({info["link"]}) ${info["price"]}') # doesnt have a filling today
                        previously_notified_or_discarded.update(dict_worth_watching.keys())     # we add the notified tickers to the set to avoid duplicate notifications next iterations , we use update after union since union gives a new copy and update modifies the existing set
                        print('Done sending messages')
                        print(f'New set of notified/discarded set is {previously_notified_or_discarded}') # we print it here and not inside the previous if to debugg and check that it was cleared after close ( so that each day starts with a an empty set and doesnt carry the notified tickers from yest )
                    print(f'Sleeping for 30 mins starting at {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                    await asyncio.sleep(60*30)  # every 30 mins
                elif nyc_time >= nyc_close_time: # we reset the notified ticker after close
                    previously_notified_or_discarded= blocked_set.copy()  # shallow copy, set gets reset after close to what we manually added as blocked, this way every day we start with the set of blocked 
                    print(f'After hours limit, Sleeping for 9 hours starting at {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                    print(f'The Blocked_set is {blocked_set}, assigned to previously_notified_set')
                    await asyncio.sleep(60*60*9) #sleep for 9 hours when the market is closed, so that we resume around 5 AM next day
                elif nyc_time <=start:
                    print(f'Sleeping for 1 hour in Premarket, time is {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                    await asyncio.sleep(60*60)  # sleep for an hour since it's probably around 4:XX AM and not worth it to check early before 7 am
            else:
                print(f'Weekend, Sleeping for 48 hours starting {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                await asyncio.sleep(60*60*48)
        except Exception:
            await me.send('Problem encountered in outside the fetch logic: \n' + '```' + traceback.format_exc()[-1700:] + '```' +'\n\nSleeping for 10 mins after failed fetched attempt at ' + datetime.datetime.now(tz=ZoneInfo('America/New_York')).strftime("%H:%M:%S"))
            print('Problem encountered in outside the fetch logic, Sleeping for 30min')
            await asyncio.sleep(60 * 30)



@bot.event
async def on_message(ctx):
    global blocked_set
    #if ctx.channel.type == 'private' : # gives 'private' if DM or 'text' if its a public text channel but it doesnt work cause it's not a string so we try the next IF, this is only here to show the logical steps 
    #    print(ctx.content)
    #    await ctx.channel.send(f'Done blocked {ctx.cotent}')
    if isinstance(ctx.channel, discord.channel.DMChannel) and ctx.author != bot.user and ctx.type != discord.MessageType.pins_add and ctx.type != discord.MessageType.reply  : # prevents the bot from going into an endless loop and check that it isnt a system message after we pin a message and also not a reply to a good filling that we want to add info 
        command = ctx.content
        parameter = command.split(' ')
        if len(parameter) == 1:  #one word DM 'LIST','CLEAR' or AAPL ( just ticker symbol to add) 
            if command == 'LIST':
                await ctx.channel.send(blocked_set)
            elif command == 'CLEAR':             
                blocked_set= set()
                await ctx.channel.send('Cleared the set')
            else: #TICKER 
                blocked_set.add(command.upper())
                await ctx.channel.send(f'Added {command.upper()} to the set')
        else:    # to remove just REMOVE Ticker or R Ticker
            blocked_set.discard(parameter[1].upper())
            await ctx.channel.send(f'Deleted {parameter[1].upper()} from the set')
            


async def bot_start():
     await bot.start(os.getenv('TOKEN',None))


# https://www.youtube.com/watch?v=nFn4_nA_yk8&t=786s&ab_channel=PatrickCollins explains the asyncio principle
# https://www.youtube.com/watch?v=Ii7x4mpIhIs&t=189s&ab_channel=JohnWatsonRooney another example

#import asyncio
#import aiohttp
#import requests
#import pprint
#import datetime


def premarket_gainers(price_limit=1):
    url = "https://quotes-gw.webullfintech.com/api/bgw/market/topGainers?regionId=6&pageIndex=1&pageSize=100"
    headers = {
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36', }
    response = requests.get(url, headers=headers)  # single call so its okay to make in synchronously
    data = response.json()
    tickers = list()
    for ticker in data['data']:
        info = ticker['ticker']
        lean_ticker = info['symbol']
        if ' ' in lean_ticker:  # sometimes a symbol like GTN-A is writen by the API as GTN A, so we eliminite all weird looking symbols
            continue
        gain = int(float(info['changeRatio']) * 100)
        price = int(float(ticker['values']['price']))
        if (price > price_limit):
            tickers.append({'ticker': lean_ticker, 'price': price, 'gain': gain})
    #pprint.pprint(tickers)
    return tickers


async def fetch_CIK(ticker_dict, session):  # we hit our own API to get the CIK then we added it to the dic;
    response = await session.get(f'https://sec.visas.tn/{ticker_dict["ticker"]}',ssl=False)  # {'ticker':'APPL',price:X,gain:Y,CIK:0123231} } we get key AAPL as k and the dict {price:X,gain:Y} as parameter ticker_dict
    response.raise_for_status()
    api_response = await response.json()
    ticker_dict['CIK'] = api_response['CIK'] # can be None found but that's okay
    return


async def add_CIKs(tickers):  # This takes the dictionary and adds the CIKs to it that we will use to get the fillings from the SEC API in the next step
    tasks = []  # tickers has the format [ {'ticker:'ACIU','gain': 19, 'price': 3},{'ticker':'ADGM','gain': 34, 'price': 3} ]
    conn = aiohttp.TCPConnector(limit_per_host=5)
    async with aiohttp.ClientSession(connector=conn) as session:  # we keep the same session for all the requests and pass it on to the individual calls
        for ticker_dict in tickers:  #
            tasks.append(fetch_CIK(ticker_dict, session))  # assembles all the tasks and then triggers them with asyncio.gather
        start = t.time()
        results = await asyncio.gather(*tasks)
        print(f'Time to get all the CIKs {t.time() - start } s')
        pprint.pprint(tickers)
        return tickers


async def get_filling(ticker_dict,session,notified_or_discarded,days_limit=30):  # we hit the SEC API to get the fillings from 30 days that has EFFECT or S-1
    today = datetime.date.today()                             # ticker_dict has format {ticker:AAPL,price:X,gain:Y,CIK:Z}
    one_month_ago = today - datetime.timedelta(days=days_limit)
    
    url = f"https://efts.sec.gov/LATEST/search-index?category=custom%20S-1&ciks={str(ticker_dict['CIK']).zfill(10)}&&forms=F-1%2CF-1MEF%2CS-1%2CS-1MEF&&startdt={one_month_ago.isoformat()}&enddt={today.isoformat()}" #this tries to pull all the S-1, S-1/A, S-1/MEF F-1 and F-1/A/MEF from the last 30 days
    response = await session.get(url,ssl=False)
    api_response = await response.json()
    hits = int(api_response['hits']['total']['value'])
    forms = api_response['hits']['hits']
    if(not hits): # this means there is no fillings of this ticker in the past 30 days that has S-1 or EFFECT
       return # returns NONE here that gets filtered on the function that called it
    else:  # means it has S-1x fillings, we now check if its an IPO, this step filters S-1 of newly listed tickers 
        url_CERT = f'https://efts.sec.gov/LATEST/search-index?category=custom&ciks={ticker_dict["CIK"]}&forms=CERT&startdt={one_month_ago.isoformat()}&enddt={today.isoformat()}' #polls if this is a new listing/IPO by checking for CERT filling last month
        response = await session.get(url_CERT,ssl=False)
        api_response = await response.json()
        if int(api_response['hits']['total']['value']):  #its an IPO, discard
            print(f'added {ticker_dict["ticker"]} to the set of discarded_notified because its an IPO')
            notified_or_discarded.add(ticker_dict['ticker'])
            print(f'notified/discarded set is : {notified_or_discarded}')
            return
    
    # if we reach here it means we have good S/F-1x fillings that are NOT an IPO, we now scan the S-1 fillings to check if they are REsale of shareholders 
        headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,fr;q=0.7',
        'cache-control': 'max-age=0',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    }
    async with aiohttp.ClientSession(headers=headers) as s:
        for form in forms: # if forms are returns we check if they match EFFECT or S-1
                latest_filling_date = forms[0]['_source']['file_date'] # this checks the date of the latest filling, if there is a good filling we involve the latest date and notify it there is a match
                id = form['_id'].split(':')  # form ['id] = "_id": "0001370053-24-000056:anab-formsx3_atm2024.htm" , we split it on the ':' which will be replace with a '/' later
                filing_number = id[0].replace('-', '')  # we replace the dashes '-' with empty spaces to construct the filling link
                filling_link = f'https://www.sec.gov/Archives/edgar/data/{int(ticker_dict["CIK"])}/{filing_number}/{id[1]}'
                print(filling_link)
                filling = await s.get(filling_link,ssl=False)
                filling_text = await filling.text()
                if 'We will not receive any' not in filling_text: # this checks if the S-1/F-1 filling is NOT a shareholders selling filling but checking for the eliminating text
                    print(f'good filling found on {ticker_dict["ticker"]}, added')
                    email_hyperlink = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker_dict["CIK"]}&owner=exclude&count=40'
                    return  {ticker_dict['ticker']: {'link':email_hyperlink,'price':ticker_dict['price'],'latest_filling_date':latest_filling_date}} # we break here as soon as we find a good one 
                else:
                    print(f'Shareholder Resale filling found on {ticker_dict["ticker"]}, discarded')
        else:   # this else means we went through all the filling of this ticker but all of them were shareholders selling fillings and not interesting ones, we wouldn't make it here if we found a good one since we have a return that will jump over this
            print(f'added {ticker_dict["ticker"]} to the set of discarded_notified')
            notified_or_discarded.add(ticker_dict['ticker'])  # here we add the ticker whole fillings are not interesting to the discarded list so that we avoid checking again next loop , to be determined if this is a good decision just in case something newer gets filed later 
            print(f'notified/discarded set is : {notified_or_discarded}')
    return

async def get_all_fillings(tickers,notified_or_discarded): # the function responsible for bundling the async API requests to the SEC API, each single call is made through function get_filling
    tasks = []
    list_worth_watching = dict()
    headers = {
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,fr;q=0.7',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    }
    conn = aiohttp.TCPConnector(limit_per_host=5)
    async with aiohttp.ClientSession(headers=headers,connector=conn) as session:
        for ticker_dict in tickers:
            if ticker_dict['ticker'] not in notified_or_discarded: # doesnt check fillings for already discard or notified tickers 
               tasks.append(get_filling(ticker_dict, session,notified_or_discarded))  # ticker is a dict {ticker:'AAPL',CIK:013494343,gain:14,price:5}
        start = t.time()
        results = await asyncio.gather(*tasks)  # returns a list of suc [ { 'QNTM': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1771885&owner=exclude&count=40'}, None (means no fillings were found for that api requests) , {'SG': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1477815&owner=exclude&count=40'} ]
        print(f'Time to get all the fillings {t.time() - start } s')
        for result in results:
            if result is not None:  # this filters the empty API requests that had no hits by taking out the Nones
                list_worth_watching.update(result)  # very important part here merges every dict in a single one to make it easier for search in the next step , end result { 'QNTM': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1771885&owner=exclude&count=40','SG': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1477815&owner=exclude&count=40'}
        #pprint.pprint(list_worth_watching)
        return list_worth_watching


async def play(notified_or_discarded): # only get all fillings updates the notified_or_discarded set
    tickers_without_cik = premarket_gainers()
    tickers_with_cik = await add_CIKs(tickers_without_cik)
    worth_watching_list = await get_all_fillings(tickers_with_cik,notified_or_discarded)
    return  worth_watching_list


if __name__ == '__main__':
    asyncio.run(bot_start())
