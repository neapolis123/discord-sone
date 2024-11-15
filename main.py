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
#https://www.youtube.com/watch?v=9nCiT_Wt3_w&ab_channel=Oliver%27sTech
#https://www.youtube.com/watch?v=UYJDKSah-Ww&ab_channel=Indently

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!',intents=intents)



@bot.event
async def on_ready():
    channel = bot.get_channel(1306738767280738354)
    start = datetime.time.fromisoformat('07:00:00')
    nyc_close_time = datetime.time.fromisoformat('20:00:00')
    previously_notified= set()
    await channel.send('Starting <@253660472803328002>')
    iteration = 0
    while (True):
        try:
            nyc_time = datetime.datetime.now(tz=ZoneInfo('America/New_York')).time()
            if start <= nyc_time <= nyc_close_time:
                iteration += 1
                print(iteration)
                print(f'Previous notified set is {previously_notified}')
                dict_worth_watching = {}
                try:
                  dict_worth_watching = await play()  # one dict with all tickers as keys {'UAVS': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=8504&owner=exclude&count=40','QUBT': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1758009&owner=exclude&count=40'}
                except Exception:                     # this dict has all the tickers that have fillings in the last 30days that include S-1 and EFFECT, we filter and notify in the next steps
                  await channel.send('<@253660472803328002>')
                  await channel.send(f'A problem has been encountered in fetching logic: \n```{traceback.format_exc()[-1700:]}``` \nSleeping for 10 mins after failed fetched attempt at {datetime.datetime.now().time().strftime("%H:%M:%S")}')
                  print(f'Problem encountered with the logi \nSleeping for 10 mins after failed fetched attempt at {datetime.datetime.now().time().strftime("%H:%M:%S")}')
                  await asyncio.sleep(60*30)
                  continue
                set_of_dict_from_logic = set(dict_worth_watching.keys())  # in order to check if we already notified these tickers we have to turn the keys into a set and compared them to the set of the previously notified tickers
                print(f'Full returned set is {set_of_dict_from_logic}')
                set_non_notified = set_of_dict_from_logic.difference(previously_notified)  # we get the tickers that weren't notified and add them to the final list that will be dispatched to users
                print(f'Non_notified_set is {set_non_notified} ')
                final_dict = dict()
                for ticker in set_non_notified:   #after having the list of tickers to be notified ( that werent previously notified ) we put them all in a one dict as we received them from the logic in play() {'AAPL':'https://linktothefilling.com','NFTLX':'https://link.com'},
                    final_dict.update({ticker:dict_worth_watching[ticker]})
                if final_dict:   #If there are tickers to be notified 
                    await channel.send('<@253660472803328002>')     #tag me 
                    for ticker, link in final_dict.items():           #this is for formating so that each ticker send on chat is a hyperlink linking to the fillings 
                        await channel.send(f'- [{ticker}]({link})')
                    previously_notified = previously_notified.union(set_non_notified)     #we add the notified tickers to the set to avoid duplicate notifications next iterations
                    print('Done sending messages')
                print(f'New set of notified set is {previously_notified}') # we print it here and not inside the previous if to debugg and check that it was cleared after close ( so that each day starts with a an empty set and doesnt carry the notified tickers from yest )
                print(f'Sleeping for 30 mins starting at {datetime.datetime.now().time().strftime("%H:%M:%S")}')
                await asyncio.sleep(60*30 )  # every 30 mins
            if nyc_time >= nyc_close_time: # we reset the notified ticker after close
                previously_notified=set()  #set gets reset after dlose
                print(f'After hours limit, Sleeping for 12 hours starting at {datetime.datetime.now().time().strftime("%H:%M:%S")}')
                await asyncio.sleep(60*60*12) #sleep for 12 hours when the market is closed
            if nyc_time <=start:
                print(f'Sleeping for 30mins in Premarket, time is {datetime.datetime.now().time().strftime("%H:%M:%S")}')
                await asyncio.sleep(60*60*3)  # sleep for an hour since it's probably around 4:XX AM and not worth it to check early before 7 am
        except Exception:
            await channel.send('<@253660472803328002>')
            await channel.send('Problem encountered in outside the fetch logic: \n' + '```' + traceback.format_exc()[-1700:] + '```' +'\n\nSleeping for 10 mins after failed fetched attempt at ' + datetime.datetime.now().time().strftime("%H:%M:%S"))
            print('Problem encountered in outside the fetch logic, Sleeping for 30min')
            await asyncio.sleep(60 * 30)

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
    pprint.pprint(tickers)
    return tickers


async def fetch_CIK(ticker_dict, session):  # we hit our own API to get the CIK then we added it to the dic;
    response = await session.get(f'https://sec.visas.tn/{ticker_dict["ticker"]}',ssl=False)  # {'ticker':'APPL',price:X,gain:Y,CIK:0123231} } we get key AAPL as k and the dict {price:X,gain:Y} as parameter ticker_dict
    response.raise_for_status()
    api_response = await response.json()
    ticker_dict['CIK'] = api_response['CIK']
    return


async def add_CIKs(tickers):  # This takes the dictionary and adds the CIKs to it that we will use to get the fillings from the SEC API in the next step
    tasks = []  # tickers has the format [ {'ticker:'ACIU','gain': 19, 'price': 3},{'ticker''ADGM','gain': 34, 'price': 3} ]
    conn = aiohttp.TCPConnector(limit_per_host=5)
    async with aiohttp.ClientSession(connector=conn) as session:  # we keep the same session for all the requests and pass it on to the individual calls
        for ticker_dict in tickers:  #
            tasks.append(fetch_CIK(ticker_dict, session))  # assembles all the tasks and then triggers them with asyncio.gather
        results = await asyncio.gather(*tasks)
        pprint.pprint(tickers)
        return tickers


async def get_filling(ticker_dict,session,days_limit=30):  # we hit the SEC API to get the fillings from 30 days that has EFFECT or S-1
    today = datetime.date.today()                             # ticker_dict has format {ticker:AAPL,price:X,gain:Y,CIK:Z}
    one_month_ago = today - datetime.timedelta(days=days_limit)
    url = f"https://efts.sec.gov/LATEST/search-index?q=EFFECT%20S-1&ciks={str(ticker_dict['CIK']).zfill(10)}&startdt={one_month_ago.isoformat()}&enddt={today.isoformat()}"
    response = await session.get(url,ssl=False)
    api_response = await response.json()
    hits = int(api_response['hits']['total']['value'])
    forms = api_response['hits']['hits']
    if(not hits): # this means there is no fillings of this ticker in the past 30 days that has S-1 or EFFECT
       return # returns NONE here that gets filtered on the function that called it
    for form in forms: # if forms are returns we check if they match EFFECT or S-1
        if ('EFFECT' in form['_source']['form'] or 'S-1' in form['_source']['form']):
            email_hyperlink = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker_dict["CIK"]}&owner=exclude&count=40'
            return {ticker_dict['ticker']: email_hyperlink}
    return


async def get_all_fillings(tickers): # the function responsible for bundling the async API requests to the SEC API, each single call is made through function get_filling
    tasks = []
    list_worth_watching = dict()
    headers = {
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,fr;q=0.7',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    }
    conn = aiohttp.TCPConnector(limit_per_host=5)
    async with aiohttp.ClientSession(headers=headers,connector=conn) as session:
        for ticker_dict in tickers:
            tasks.append(get_filling(ticker_dict, session))  # ticker is a dict {ticker:'AAPL',CIK:013494343,gain:14,price:5}
        results = await asyncio.gather(*tasks)  # returns a list of suc [ { 'QNTM': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1771885&owner=exclude&count=40'}, None (means no fillings were found for that api requests) , {'SG': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1477815&owner=exclude&count=40'} ]
        for result in results:
            if result is not None:  # this filters the empty API requests that had no hits by taking out the Nones
                list_worth_watching.update(result)  # very important part here merges every dict in a single one to make it easier for search in the next step , end result { 'QNTM': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1771885&owner=exclude&count=40','SG': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1477815&owner=exclude&count=40'}
        pprint.pprint(list_worth_watching)
        return list_worth_watching


async def play():
    tickers_without_cik = premarket_gainers()
    tickers_with_cik = await add_CIKs(tickers_without_cik)
    worth_watching_list = await get_all_fillings(tickers_with_cik)
    return  worth_watching_list


if __name__ == '__main__':
    asyncio.run(bot_start())

