headers =  {
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

# https://www.youtube.com/watch?v=nFn4_nA_yk8&t=786s&ab_channel=PatrickCollins explains the asyncio principle
# https://www.youtube.com/watch?v=Ii7x4mpIhIs&t=189s&ab_channel=JohnWatsonRooney another example



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

blocked_dict = dict() # will be of the format {'AMIX':'2024-03-13','BLOCKED':'BLOCKED'}
number_of_days_for_fillings = 30 # 
currently_running = set() # if something has been notified previously but is currently running we put it here so that we only notified once more 
running_threshold = 30 #% the percentage over which something is considered running
gainers_upper_limit = 20  #$ we filter out tickers above 30 dollars 
gainers_lower_limit = 1 # we filter out penny tickers
errors = list() # when there is an error fetching we save the timestamp here 

@bot.event
async def on_ready():
    #channel = bot.get_channel(1306738767280738354) good to keep if i decide to change from DMS to channels posting
    global currently_running
    me = await bot.fetch_user(253660472803328002) # my discord id 
    start = datetime.time.fromisoformat('04:00:00')
    nyc_close_time = datetime.time.fromisoformat('20:00:00')
    await me.send('Starting\n')
    iteration = 0
    previously_notified_or_discarded = dict() # will be of the format {'AMIX':'2024-03-13','FPAY':'2023-09-09','UNTZ':'IPO'}
    while (True):
        try:
            nyc_date = datetime.datetime.now(tz=ZoneInfo('America/New_York'))
            nyc_time = nyc_date.time()
            today = nyc_date.weekday()
            if  0 <= today <= 4:  # if weekend just sleep for 48 hours
                if start <= nyc_time <= nyc_close_time: # If between 4am and 8pm inclusive
                    iteration += 1
                    print(iteration)
                    dict_worth_watching = {}
                    previously_notified_or_discarded.update(blocked_dict) #adds the new blocked dict to the current discarded/notifie, we do it here , might be inefficient but this way the blocked tickers are added one iteration later intead of one day later at close
                    try:  #the previously_notified dict here is updated inside play to add IPOs and Reselling Shareholders S-1s, its shared between the inner logic and this outer logic , it is reset at the end of every day
                      dict_worth_watching = await play(previously_notified_or_discarded)  # one dict with all tickers as keys {'UAVS': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=8504&owner=exclude&count=40',price:5,latest_filling_date:2024-02-10},'QUBT': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1758009&owner=exclude&count=40',price:10,latest_filling_date:2024-02-10} }
                    except Exception: # this dict has all the tickers that have fillings in the last 30days that include S-1 and F-1, if we reached this point, it means that these tickers will be notified because they were filtered as not preivously notified/discard in 'get_fillings' and if a a ticker has a filling but it's a seller shareholder one it will be added to the discarded without making it to this step
                      await me.send(f'A problem has been encountered in fetching logic: \n```{traceback.format_exc()[-1700:]}``` \nSleeping for 30 mins after failed fetched attempt at {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                      print(f'Problem encountered with the logic \nSleeping for 30 mins after failed fetched attempt at {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                      await asyncio.sleep(60*30)
                      continue
                    print(f'the set to be notified is {set(dict_worth_watching.keys())}') # the set that we got from the logic {'UAVS': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=8504&owner=exclude&count=40',price:5},'QUBT': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1758009&owner=exclude&count=40',price:10} }
                    #print(f'notified/discarded set is {previously_notified_or_discarded}') # for ease of debugging in the future
                    if dict_worth_watching:   #If there are tickers to be notified , the dict has the form of {‘AAPL':{price:5,link:'https://....',latest_filling_date:2024-02-10},'NFLX':{price:5,link:'https://....',latest_filling_date:2024-02-10}}
                        for ticker, info in dict_worth_watching.items():    # ticker is 'NFLX' and info is a dict {price:5, link:'https://....', latest_filling_date:2024-02-10}
                            if info['gain'] >= running_threshold : # the ticker to notify is running, we don't care if we previously notified this or not ( both filling or running)
                                #if ticker in previously_notified_or_discarded.keys():
                                    if info['latest_filling_date'] == str(datetime.datetime.today().date()) :
                                        await me.send(f'- [{ticker}]({info["link"]}) ${info["price"]} - Is currently running + filling today')
                                    else:
                                        await me.send(f'- [{ticker}]({info["link"]}) ${info["price"]} - Is currently running with a filling')
                                #else:  
                                #    if info['latest_filling_date'] == str(datetime.datetime.today().date()) :
                                #        await me.send(f'- [{ticker}]({info["link"]}) ${info["price"]} - Is currently running + filling today')
                                #    else :
                                #        await me.send(f'- [{ticker}]({info["link"]}) ${info["price"]} - Is currently running with a filling')
                                    currently_running.add(ticker) # to avoid to be notified on every iteration, will be used in get_filling() to filter out previously notified tickers 
                                    print(f'the currently running set is : {currently_running}')
                            elif info['latest_filling_date'] == str(datetime.datetime.today().date()): # this checks if it has a filling today, quality of life to avoid opening everyday when something is relevant over multiple days but awaiting an amendment
                               await me.send(f'- [{ticker}]({info["link"]}) ${info["price"]} - Has a filling today') 
                            else:
                               await me.send(f'- [{ticker}]({info["link"]}) ${info["price"]}') # doesnt have a filling today
                            previously_notified_or_discarded.update({ticker:info['latest_filling_date']})  # we add the notified tickers to the set to avoid duplicate notifications next iterations , we use update after union since union gives a new copy and update modifies the existing set
                        print('Done sending messages')
                    print(f'New set of notified/discarded set is {previously_notified_or_discarded}') # we print it here and not inside the previous if to debugg and check that it was cleared after close ( so that each day starts with a an empty set and doesnt carry the notified tickers from yest )
                    print(f'Sleeping for 10 mins starting at {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                    await asyncio.sleep(60*10)  # every 10  mins
                elif nyc_time >= nyc_close_time: # we reset the notified ticker after close
                    seconds_until_4AM = (60*60*7 + ( (60 - datetime.datetime.now().time().minute) * 60 )+ (60 - datetime.datetime.now().time().second ))
                    print(f'After hours limit, Sleeping for  {str(datetime.timedelta(seconds=seconds_until_4AM))} starting at {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}PM NYC ')
                    #print(f'The Blocked_set is {blocked_dict}, assigned to previously_notified_set') # just to have it visually visible/debug 
                    currently_running = set()
                    await asyncio.sleep(seconds_until_4AM) # sleep just enough to start again at 4AM exactly, we do this by waiting until the hour is ended after the market is closed that is until 21H and then we wait 8 hours from there , we calculate this by taking current minutes and subsracting them from 60 minutes and then multiply by 60 to get how many seconds until the next hours starts
                elif nyc_time <=start:
                    print(f'Sleeping for 1 hour in Premarket, time is {datetime.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%H:%M:%S")}')
                    await asyncio.sleep(60*60)  # sleep for an hour since it's probably Before 4:XX AM 
            else: # its the weekend
                 now  = datetime.datetime.now(tz=ZoneInfo("America/New_York"))
                 extraday = 60*60*24  if today==4 else 0 #if saturday we add an extra 24 hours otherwise nothing 
                 next_midnight = (now + datetime.timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0) # since midnight is the next day, we add 1 day to the current time and then roll back to 0 all the hours minutes seconds and micro to get midnight. this will be midnight 
                 seconds_until_midnight = (next_midnight - now).seconds # the number of seconds from now to midnight 
                 seconds_until_Monday_4am = ( seconds_until_midnight + extraday + 60*60*4 + 60  ) # here we wait until midnight, then we add 24 hours if we are in saturday to sleep through sunday, then sleep 4 hours until 4am plus 60 seconds i.e 1 minute to avoid getting false gainers at exactly 4 am from webull
                 previously_notified_or_discarded= dict()  #  the previously notified set gets reset after close, it gets updated with the blocked set on every iteration in the upper logic
                 print(f'Weekend, Sleeping for {str(datetime.timedelta(seconds=seconds_until_Monday_4am))} starting {now.strftime("%H:%M:%S")} NYC time ')
                 await asyncio.sleep(seconds_until_Monday_4am)

        except Exception:
            await me.send('Problem encountered in outside the fetch logic: \n' + '```' + traceback.format_exc()[-1700:] + '```' +'\n\nSleeping for 10 mins after failed fetched attempt at ' + datetime.datetime.now(tz=ZoneInfo('America/New_York')).strftime("%H:%M:%S"))
            print('Problem encountered in outside the fetch logic, Sleeping for 30min')
            await asyncio.sleep(60 * 30)



@bot.event
async def on_message(ctx):
    global blocked_dict
    #if ctx.channel.type == 'private' : # gives 'private' if DM or 'text' if its a public text channel but it doesnt work cause it's not a string so we try the next IF, this is only here to show the logical steps 
    #    print(ctx.content)
    #    await ctx.channel.send(f'Done blocked {ctx.cotent}')
    if isinstance(ctx.channel, discord.channel.DMChannel) and ctx.author != bot.user and ctx.type != discord.MessageType.pins_add and ctx.type != discord.MessageType.reply  : # prevents the bot from going into an endless loop and check that it isnt a system message after we pin a message and also not a reply to a good filling that we want to add info 
        command = ctx.content
        parameter = command.split(' ')
        if len(parameter) == 1:  #one word DM 'LIST','CLEAR' or AAPL ( just ticker symbol to add) 
            if command == 'LIST':
                await ctx.channel.send(blocked_dict)
            elif command == 'CLEAR':             
                blocked_dict= set()                          # worth noting that all modifications to the blocked set are only applied the next day
                await ctx.channel.send('Cleared the set')
            elif command == 'ERRORS':
                if len(errors) :
                    await ctx.channel.send(f'{errors} with length {len(errors)}')
                else:   
                    await ctx.channel.send(f'No Errors')
            else: # only the TICKER is typed
                blocked_dict.update({command.upper():'Blocked'})
                await ctx.channel.send(f'Added [{command.upper()}] to the set')
        else:    # this means we have multiple parameters either REMOVE APPL 
            if parameter[0] == 'REMOVE':
                del blocked_dict[parameter[1].upper()]
                await ctx.channel.send(f'Deleted [{parameter[1].upper()}] from the set')
            else: # or just a list of tickers to add one after the others APPL NFLX MOXL UMAC
                for i in parameter:
                    blocked_dict.update({i.upper():'Blocked'}) 
                    await ctx.channel.send(f'Added [{i.upper()}] to the set')
        
   


async def bot_start():
     await bot.start(os.getenv('TOKEN',None))



def premarket_gainers(lower_price_limit=gainers_lower_limit,upper_price_limit=gainers_upper_limit): # we filter out tickers than are pennies ( Sub 1 dollar) and mid-large caps ( over 30 dollar which is already high )
    url = "https://quotes-gw.webullfintech.com/api/bgw/market/topGainers?regionId=6&pageIndex=1&pageSize=150" # the number of tickers is at the end 
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
        price = int(float(ticker['values']['price'])) # will be rounded down, 1.4 will be 1 and 2.6 will be 2 as an int
        if (price > lower_price_limit and price < upper_price_limit): # excluse to make sure tickers with 1.X format dont get detected, to be determined if this good or not
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
    conn = aiohttp.TCPConnector(limit_per_host=5,limit=30)
    async with aiohttp.ClientSession(connector=conn) as session:  # we keep the same session for all the requests and pass it on to the individual calls
        for ticker_dict in tickers:  #
            tasks.append(fetch_CIK(ticker_dict, session))  # assembles all the tasks and then triggers them with asyncio.gather
        start = t.time()
        results = await asyncio.gather(*tasks)
        print(f'Time to get all the CIKs {t.time() - start } s')
        pprint.pprint(tickers)
        return tickers


async def get_filling(ticker_dict,session,notified_or_discarded,days_limit=number_of_days_for_fillings):  # we hit the SEC API to get the fillings from 30 days that has EFFECT or S-1
    global errors
    today = datetime.date.today()                             # ticker_dict has format {ticker:AAPL,price:X,gain:Y,CIK:Z}
    one_month_ago = today - datetime.timedelta(days=days_limit)
    
    if notified_or_discarded.get(ticker_dict['ticker'])=='Blocked' or notified_or_discarded.get(ticker_dict['ticker'])=='IPO': 
        return
    
    url = f"https://efts.sec.gov/LATEST/search-index?category=custom%20S-1&ciks={str(ticker_dict['CIK']).zfill(10)}&&forms=F-1%2CF-1MEF%2CS-1%2CS-1MEF&&startdt={one_month_ago.isoformat()}&enddt={today.isoformat()}" #this tries to pull all the S-1, S-1/A, S-1/MEF F-1 and F-1/A/MEF from the last 30 days
    response = await session.get(url,ssl=False)
    if response.status == 403: # sometimes the server just throttles us
        print(f"acccess was denied for ticker {ticker_dict['ticker']} with url: {url} , was skipped") # we print in the console but since we don't check the console all the time
        error_time = datetime.datetime.now(ZoneInfo('Africa/Tunis')) # we snapshot the timestamp
        formated_error_timestamp_tunis_time = str(error_time.date()) + ' ' + str(error_time.strftime("%H:%M")) # format it to be easily readable
        errors.append(formated_error_timestamp_tunis_time) # then save it in a set to be consulted on demand 
        print(f'error timestamp {formated_error_timestamp_tunis_time} added ') # we print for debugging
        return
    api_response = await response.json() # an example at https://efts.sec.gov/LATEST/search-index?q=S-1&category=form-cat0&ciks=0001956955&entityName=Unusual%20Machines%2C%20Inc.%20%20(CIK%200001956955)&forms=-3%2C-4%2C-5&startdt=2019-11-29&enddt=2024-11-29
    hits = int(api_response['hits']['total']['value'])
    forms = api_response['hits']['hits'] # returns a list of  dicts (each dict is a form ) 
    if(not hits): # this means there is no fillings of this ticker in the past 30 days that has S-1 or EFFECT, equal to 0 if there is none
       return # returns NONE here that gets filtered on the function that called it
    else:  # means it has S-1x fillings, we now check if its an IPO, this step filters S-1 of newly listed tickers 
        latest_filling_date = forms[0]['_source']['file_date'] # this checks the date of the latest filling (they are ordered latest on top), if there is a good filling we involve the latest date and notify it there is a match
        url_CERT = f'https://efts.sec.gov/LATEST/search-index?category=custom&ciks={ticker_dict["CIK"]}&forms=CERT&startdt={one_month_ago.isoformat()}&enddt={today.isoformat()}' #polls if this is a new listing/IPO by checking for CERT filling last month
        response = await session.get(url_CERT,ssl=False)
        api_response = await response.json()
        if int(api_response['hits']['total']['value']):  #its an IPO, discard
            print(f'added {ticker_dict["ticker"]} to the set of discarded_notified because its an IPO')
            notified_or_discarded.update({ticker_dict['ticker']:'IPO'}) # we update the notified_dict with {'UAVS':'2014-12-12'}
            #print(f'notified/discarded set is : {notified_or_discarded}') # for debugging
            return

        # if we reach here it means we have good S/F-1x fillings that are NOT an IPO, we now scan the S-1 fillings to check if they are Resale of shareholders 
        
        # this block is a filter that discards previously notified or currently running tickers with no new fillings                 
        if  ticker_dict['ticker'] in notified_or_discarded.keys(): # was this ticker previously discarded/notified and NOT and IPO/blocked  
            if ticker_dict['gain'] < running_threshold: #is the ticker not running now, this is made in order to notify us AGAIN that a ticker previously notified on this week is CURRENTLY running, the running_threshhold is the % over which we want to consider something to be running , 30% for us 
                if latest_filling_date == notified_or_discarded[ticker_dict['ticker']]: # previously notified and not blocked/IPO and is NOT running + no newer fillings, we discard it
                    return  # it is not running and no newer fillings, discard
                        # indirectly , if a ticker is not running and has newer filling they are not discard and jump to the async block to be processed for selling shareholder 
            else:  # a ticker that is currently running AND previously notified 
                if ticker_dict['ticker'] in currently_running and latest_filling_date == notified_or_discarded[ticker_dict['ticker']] : # have we notified that this ticker is running and if even if yes, we check if it has a newer filling since last time, if yes we don't discard it and let the logic update it 
                    return # it has been notified that is running and doesnt have a newer filling, we discard

        # Here we filter for shareholder resale fillings and discard them,and if it's a good filling we forward it to be notified 

        async with aiohttp.ClientSession(headers=headers) as s: # means we got a newer filling for a notified or a discarded ticker or simply first time check for something that has non IPO fillings, we check if they are good or not inside 
            for form in forms: # if forms are returned we check if they match F-1/X or S-1/X,
                    id = form['_id'].split(':')  # form ['id] = "_id": "0001370053-24-000056:anab-formsx3_atm2024.htm" , we split it on the ':' which will be replace with a '/' later
                    filing_number = id[0].replace('-', '')  # we replace the dashes '-' with empty spaces to construct the filling link
                    filling_link = f'https://www.sec.gov/Archives/edgar/data/{int(ticker_dict["CIK"])}/{filing_number}/{id[1]}'
                    print(filling_link)
                    filling = await s.get(filling_link,ssl=False)
                    filling_text = await filling.text()
                    eliminating_text = ['will not receive any proceeds','will not receive any of the proceeds']
                    if 'This page is temporarily unavailable' in filling_text: # checks if the SEC server is down, happenes from time time, in this case we basically reject the ticker so we don't notify every ticker that has S-1
                        print(f"SEC site is down when trying to retreive ticker {ticker_dict['ticker']} with url: {filling_link}")
                        continue # try with next filling
                    if all(el not in filling_text for el in eliminating_text) : #longer version :'will not receive any proceeds' not in filling_text and 'will not receive any of the proceeds' not in filling_text: # this checks if the S-1/F-1 filling is NOT a shareholders selling filling by checking for the eliminating text
                        if 'SUBJECT TO COMPLETION' not in filling_text.upper(): # sometimes an annex without the WILL NOT RECEIVE ANY PROCEEDS is filled and its detected as a good filling althought its belongs to a shareholder resale, to make sure we eliminate those we check for string 'SUBJECT TO COMPLETION' , example https://www.sec.gov/Archives/edgar/data/1874252/000121390024107013/ea0224137-f1a2_mainz.htm
                            print(f'Annex found with url {filling_link}, filling ignored') # for debugging purposes 
                            continue # we jump to the next filling  
                        print(f'good filling found on {ticker_dict["ticker"]}') 
                        email_hyperlink = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker_dict["CIK"]}&owner=exclude&count=200'
                        return  {ticker_dict['ticker']: {'link':email_hyperlink,'price':ticker_dict['price'],'latest_filling_date':latest_filling_date,'gain':ticker_dict['gain']}} # we break here as soon as we find a good one 
                    else:
                        print(f'Shareholder Resale filling found on {ticker_dict["ticker"]}, discarded')
            else:   # this else means we went through all the filling of this ticker but all of them were shareholders selling fillings and not interesting ones, we wouldn't make it here if we found a good one since we have a return that will jump over this
                print(f'added {ticker_dict["ticker"]} to the set of discarded_notified')
                notified_or_discarded.update({ticker_dict['ticker']:latest_filling_date})  # here we add the ticker whole fillings are not interesting to the discarded list so that we avoid checking again next loop , to be determined if this is a good decision just in case something newer gets filed later 
                #print(f'notified/discarded set is : {notified_or_discarded}') 
    return  

 # the function responsible for bundling the async API requests to the SEC API, each single call is made through function get_filling
async def get_all_fillings(tickers,notified_or_discarded): # tickers is a list of dicts [ {'CIK':'000129847','ticker:'ACIU','gain': 19, 'price': 3},{'CIK':'000129847','ticker':'ADGM','gain': 34, 'price': 3} ], notified_or_discard is a dict with format {'AAPL':'2024-12-25','NFLX':'2023-08-30'}
    tasks = []
    list_worth_watching = dict()
    headers = {
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,fr;q=0.7',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    }
    conn = aiohttp.TCPConnector(limit_per_host=8)
    async with aiohttp.ClientSession(headers=headers,connector=conn) as session:
        for ticker_dict in tickers:
            #if ticker_dict['ticker'] not in notified_or_discarded: # doesnt check fillings for already discard or notified tickers 
               tasks.append(get_filling(ticker_dict, session,notified_or_discarded))  # ticker is a dict {ticker:'AAPL',CIK:013494343,gain:14,price:5}, We pass the whole dict of notified/discarded dict without any filtering
        start = t.time()
        results = await asyncio.gather(*tasks)  # returns a list of suc [ { 'QNTM': {link:'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1771885&owner=exclude&count=40',price:3,latest_filling_date:2024-24-10}}, None (means no fillings were found for that api requests) ,{  'SG': {'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1477815&owner=exclude&count=40',price:3,latest_filling_date:2024-24-10} }]
        print(f'Time to get all the {len(tickers)} fillings {t.time() - start }s')
        for result in results:
            if result is not None:  # this filters the empty API requests that had no hits by taking out the Nones
                list_worth_watching.update(result)  # very important part here merges every dict in a single one to make it easier for search in the next step , end result { 'QNTM': link:{'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1771885&owner=exclude&count=40',price:3,latest_filling_date:2024-10-08},'SG': {'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1477815&owner=exclude&count=40',price:3,latest_filling_date:2024-10-08} }
        #pprint.pprint(list_worth_watching)
        return list_worth_watching


async def play(notified_or_discarded): # only get all fillings updates the notified_or_discarded dict
    tickers_without_cik = premarket_gainers()
    tickers_with_cik = await add_CIKs(tickers_without_cik)
    worth_watching_list = await get_all_fillings(tickers_with_cik,notified_or_discarded)
    return  worth_watching_list


if __name__ == '__main__':
    asyncio.run(bot_start())
