import asyncio
import sys
import time
import requests
import tweepy,logging
import aiohttp
 

 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

Ticker_url = 'https://basesearchV3.onrender.com/ticker' 
SearchUserTweet_url = 'https://basesearchV3.onrender.com/SearchUserTweet'

# Ticker_url = 'http://127.0.0.1:8000/ticker'
# SearchUserTweet_url = 'http://127.0.0.1:8000/SearchUserTweet'


async def AggregateScore(tickerPriceData:list) ->dict:
    symbol_data = {}
    for price_items in tickerPriceData:
        for symbol,timeframe_data in price_items.items():
            if isinstance(timeframe_data,list):
                symbol_data[symbol] = sum(price_data['score'] for price_data in timeframe_data )
    
    return symbol_data

# tweetData = {'contracts':[1,2,4],'ticker_names':['BTC','ETH','SOL'],'date_tweeted':'2025-07-01 08:08:00'}
async def TweetdataProcessor(tweetData:dict,timeframe:str):
    # url = 'http://127.0.0.1:8000/ticker'
    # url = 'https://basesearch2.onrender.com/ticker' 
    contracts = tweetData['contracts']
    tickers = ' '.join(tweetData['ticker_names'])
    date_tweeted = tweetData['date_tweeted'] 
    
    if contracts:
        pass
    if tickers:
        params ={
        'tickers':tickers,
        'start_date':date_tweeted,
        'timeframe':timeframe
        }
        response = requests.get(url=Ticker_url,params=params)
        if response.status_code == 200:
            data = response.json()
            tickers_scores = await asyncio.create_task(AggregateScore(data))
            return tickers_scores
        else:
            pass
    
        
# asyncio.run(TweetdataProcessor(tweetData,'5'))
async def processUsertweetedTicker_Contract(userTweetData:list,timeframe:str):
    logging.info('Processing User Tweeeted Tickers And Contract')
    username = list(userTweetData.keys())[0]
    userfinalData = {username:[]}
    tweetDatas = list(userTweetData.values())[0]
    

    userTickerScores_task = [TweetdataProcessor(tweetData,timeframe) for tweetData in tweetDatas]
    userTickerScores = await asyncio.gather(*userTickerScores_task)
    userfinalData[username] = userTickerScores
    return userfinalData

async def RequestUserTweets(username:str,limit=None):
    logging.info('Requesting User Tweets')
    # userTweets_url = 'http://127.0.0.1:8000/SearchUserTweet'
    if limit != None:
        params = {
            'username':username,
            'limit':limit
        }
    else:
        params = {
            'username':username
        }

    async with aiohttp.ClientSession() as session:
        async with session.get(url=SearchUserTweet_url,params=params) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                logging.error(f'Error Fetching User Tweets. Code:{result}')
   


async def tickerCalled_AndScore(results:list) ->dict:
    logging.info('Calculating Scores')
    userResult = {}
    try:
        for userData in results:
            userName = list(userData.keys())[0]
            tickerDatas = list(userData.values())[0]
            tickersCalled = 0
            totalScore = 0
            for tickerdata in tickerDatas:
                if tickerdata == None:
                    continue
                tickersCalled += len(list(tickerdata.keys()))
                totalScore  += sum( score for score in list(tickerdata.values()))
            userResult[userName] = {
                                'TickerCalled':tickersCalled,
                                'TotalScore':totalScore    }
            if tickersCalled == 0:
                continue
            average = float(totalScore/tickersCalled)
            userResult[userName]['averageScore'] = average 
    except:
        pass             
    return userResult

# Entry
def searchKeyword(keyword:str,date:str,timeframe:str,from_date:str|None = None,limit:int = 1,userTweetLimit=10):
    logging.info('Activating Searching For Keyword Match On Twitter')
    # call '/search/{keyword}/{date}' with the keyword
    # call /SearchUserTweet' user eachh usernme
    try:
        async def main():
            EarlyTweeters = []
            url = f'https://basesearchv3.onrender.com/search/{keyword}/{date}'
            
            params = {
                'from_date':from_date,
                'limit':limit 
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url,params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        if  result:
                            EarlyTweeters = [earlyTweet['userName'] for earlyTweet in result if earlyTweet]
                        else:
                            return {'Error': 'No Early Tweeters!'}
                    else:
                        return {'Error': f'Couldnt Request For This Keyword {keyword}'}
            
            UserTweet_task = [RequestUserTweets(username,userTweetLimit) for username in EarlyTweeters ]
            userData = await asyncio.gather(*UserTweet_task)
            logging.info('Fetched User Tweet Data')
            # userData = [{'onah':[{'contracts':[1,2,4],'ticker_names':['btc','sol'],'date_tweeted':'2025-07-22 10:20:00'},{'contracts':[1,2,4],'ticker_names':['btc','sol'],'date_tweeted':'2025-07-21 09:00:00'}]},{'inno':[{'contracts':[1,2,4],'ticker_names':['ltc','sol'],'date_tweeted':'2025-07-22 09:00:00'},{'contracts':[1,2,4],'ticker_names':['ada','bnb'],'date_tweeted':'2025-07-18 10:00:00'}]}]
            usserDataTask = [processUsertweetedTicker_Contract(userTweetData,timeframe) for userTweetData in userData]
            results = await asyncio.gather(*usserDataTask)
            userResult = await tickerCalled_AndScore(results)
            if userResult:
                return userResult
        userResult = asyncio.run(main())
        return userResult
    except Exception as e:
        return {'Error': f'Error  Occured {e}'}
   

# keyword = 'GMX hacked OR Exploited OR Exploit OR Hack'
# date = '2025-07-09'
# timeframe = '10,20'
# from_date = '2025-07-08'
# early_limit = 5
# userTweetToFetch = 5
# asyncio.run(searchKeyword(keyword,date,timeframe,from_date,early_limit,userTweetToFetch))



    






