import asyncio
import json
import sys
import time,os
import streamlit as st
import pandas as pd
import requests
import tweepy,logging
import aiohttp
 

 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# Ticker_url = 'https://basesearch2.onrender.com/ticker' 
# SearchUserTweet_url = 'https://basesearch2.onrender.com/SearchUserTweet'

Ticker_url = 'https://basesearchv3-71083952794.europe-west3.run.app/ticker'
SearchUserTweet_url = 'https://basesearchv3-71083952794.europe-west3.run.app/SearchUserTweet'

# Ticker_url = 'https://basesearchv3.onrender.com/ticker'
# SearchUserTweet_url = 'https://basesearchv3.onrender.com/SearchUserTweet'

GEMINI_API = os.environ.get('GEMINIKEY')
GEMINI_URL =  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"





def GeminiRefine(tweet_text:str=None,Ai_assits_Data:dict=None):
    search_prompt = f'You are an expert at analyzing cryptocurrency-related tweets and news. Based on the context of the provided text, extract the ticker symbol(s) of the main cryptocurrency or token being discussed. If the text focuses on a crypto platform (e.g., an exchange or blockchain) rather than a specific token, identify and return the ticker symbol of the platform’s native token, if applicable (e.g., Telegram → TON, Binance → BNB). If the text mentions a founder, team member, or associate tied to a cryptocurrency or platform, extract the ticker symbol of the specific token associated with them (e.g., Pavel Durov → TON, Vitalik Buterin → ETH, Anatoly Yakovenko → SOL). Use known associations between founders, platforms, and tokens to infer the token even if not explicitly mentioned. If multiple tokens are mentioned, prioritize the token(s) that are the primary focus of the text based on context. If no specific token, platform, or founder is mentioned, or if the focus is unclear, return "None." Only return the ticker symbol(s) (e.g., BTC, ETH, SOL) without additional explanation.'
    Ai_prompt = f"""
        I have token performance data after Twitter calls. 
        Each value is the % change in price relative to the tweet timestamp 
        at different timeframes (1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 24h).

        Data: {Ai_assits_Data}

        Task:
        1. Calculate the average % return for each timeframe across all tokens.
        2. Identify the single best timeframe (minutes or hours) that gives the highest average return.
        3. Provide ONLY:
            - The recommended timeframe and  the average percentage increase from this timeframe, by formating  it this way "Recommended Timeframe: Answer."
            - One concise explaining why that timeframe was chosen.
        """
    if Ai_assits_Data:
        Ai_input_data = f'''{Ai_prompt} Data: {Ai_assits_Data}'''
    else:
        Ai_input_data = f'''{search_prompt} Tweet: {tweet_text}'''

    headers = {
        "x-goog-api-key": GEMINI_API,
        "Content-Type": "application/json"
    }  
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": Ai_input_data
                    }
                ]
            }
        ],
        "generationConfig": {
            "thinkingConfig": {
                "thinkingBudget": 0
            }
        }
    }
            
    response = requests.post(url=GEMINI_URL,json=payload,headers=headers)
    if response.status_code == 200:
        result =  response.json()
        token_mentioned = result['candidates'][0]['content']['parts'][0]['text']

        if Ai_assits_Data:
            return token_mentioned
       
        if token_mentioned != 'None':
            token_mentioned = token_mentioned.split(',')
            return token_mentioned
        else:
            empty = []
            return empty
    else:
        empty = []
        return empty

async def AggregateScore(tickerPriceData:list) ->dict:
    symbol_data = {}
    for price_items in tickerPriceData:
        for symbol,timeframe_data in price_items.items():
            if isinstance(timeframe_data,list):
                symbol_data[symbol] = sum(price_data['score'] for price_data in timeframe_data )
    
    return symbol_data

# tweetData = {'contracts':[1,2,4],'ticker_names':['BTC','ETH','SOL'],'date_tweeted':'2025-07-01 08:08:00'}
async def TweetdataProcessor(tweetData:dict,timeframe:str,singleHandSearch:str|None=None,simpleSearch:bool|None=None):
    # Simple parameter denotes to get only the ticker performance without the score
    # url = 'http://127.0.0.1:8000/ticker'
    # url = 'https://basesearch2.onrender.com/ticker'
    contracts = tweetData['contracts']
    tickers = ' '.join(tweetData['ticker_names'])
    date_tweeted = tweetData['date_tweeted'] 
    followers = tweetData['followers']

    if contracts:
        pass
    if tickers:
        params ={
        'tickers':tickers,
        'start_date':date_tweeted,
        'timeframe':timeframe,
        }

        response = requests.get(url=Ticker_url,params=params)
        if response.status_code == 200:
            data = response.json()
            if simpleSearch:
                data.append({'followers':followers}) # Added Newly
                return data
            tickers_scores = await asyncio.create_task(AggregateScore(data))
            if singleHandSearch:
                tickers_scores['date_tweeted'] = date_tweeted
            return tickers_scores
        else:
            pass
    
async def processUsertweetedTicker_Contract(userTweetData:list,timeframe:str,mode:str|None=None,simpleSearch:bool |None =None):
    logging.info('Processing User Tweeeted Tickers And Contract')
    username = list(userTweetData.keys())[0]
    userfinalData = {username:[]}
    tweetDatas = list(userTweetData.values())[0]

    userTickerScores_task = [TweetdataProcessor(tweetData=tweetData,timeframe=timeframe,singleHandSearch=mode,simpleSearch=simpleSearch) for tweetData in tweetDatas]
    userTickerScores = await asyncio.gather(*userTickerScores_task)
    if simpleSearch and not mode:
        userfinalData[username] = userTickerScores[0]
    elif simpleSearch and mode:
        userfinalData[username] = userTickerScores
    else:
        userfinalData[username] = userTickerScores
    return userfinalData

async def RequestUserTweets(username:str,limit=None) ->dict:
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
def searchKeyword(keyword:str,date:str,timeframe:str,from_date:str|None = None,time:str|None=None,simpleSearch:str|None=None,followers_threshold:int|None=None,limit:int = 1,userTweetLimit=10):
    from datetime import datetime
    logging.info('Activating Searching For Keyword Match On Twitter')
    tickers = GeminiRefine(keyword)
    if not tickers:
        # st.error('No Ticker Matching  This Tweet Was Found!! Reconstruct The Keyword!')
        return {'Error':'No Ticker Matching  This Tweet Was Found!! Reconstruct The Keyword!'}
   


    # SimpleSearch is use to denote the search for Early tweet account performance
    # The performance is only the the news that is been search and not  On the thier past Tweets

    # call '/search/{keyword}/{date}' with the keyword
    # call /SearchUserTweet' with eachh usernme
    try:
        async def main():
            EarlyTweeters = []
            # url = f'http://127.0.0.1:8000/search/{keyword}/{date}'
            url = f'https://basesearchv3-71083952794.europe-west3.run.app/search/{keyword}/{date}'
            # url = f'https://basesearchv3.onrender.com/search/{keyword}/{date}'
            params = {}
            if from_date and time:
                params = {
                    'from_date':from_date,
                    'limit':limit, 
                    'time_search': str(time),
                    'followers_threshold':followers_threshold
                }
            elif not from_date and time != None :
                if time:
                    params = {
                        'limit':limit, 
                        'time_search': str(time),
                        'followers_threshold':followers_threshold
                    }
            elif not time and from_date != None:
                params = {
                    'limit':limit, 
                    'from_date':from_date,
                    'followers_threshold':followers_threshold
                    
                }
            if not params:
                return {'Error':'Please Choose Date To Search From'}
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url,params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        try:
                            if  result:
                                EarlyTweeters = [earlyTweet['userName'] for earlyTweet in result if earlyTweet]
                            else:
                                return {'Error': 'No Early Tweeters!'}
                        except:
                            return {'Error': 'No Tweet Fetched. Try Again Please'}
                    else:
                        return {'Error': f'Couldnt Request For This Keyword {response.status}'}
            # this is where we call @app.get("/ticker") for processing of ticker
            # calling with result
            simpleSearch = True
            if not simpleSearch:
                UserTweet_task = [RequestUserTweets(username,userTweetLimit) for username in EarlyTweeters ]
                userData = await asyncio.gather(*UserTweet_task)
            else:
                userData =  [{userdata['userName']: [{'ticker_names': tickers,# ['ADA','BTC'],
                                                    'contracts':[],
                                                    'followers':userdata['followers'],
                                                    'date_tweeted':datetime.strptime(userdata['createdAt'],"%a %b %d %H:%M:%S %z %Y").strftime("%Y-%m-%d %H:%M")+":00"}]
                                                    } 
                                                    for userdata in result]
            
            logging.info('Fetched User Tweet Data')
           
            # userData = [{'onah':[{'contracts':[1,2,4],'ticker_names':['btc','sol'],'date_tweeted':'2025-07-22 10:20:00'},{'contracts':[1,2,4],'ticker_names':['btc','sol'],'date_tweeted':'2025-07-21 09:00:00'}]},{'inno':[{'contracts':[1,2,4],'ticker_names':['ltc','sol'],'date_tweeted':'2025-07-22 09:00:00'},{'contracts':[1,2,4],'ticker_names':['ada','bnb'],'date_tweeted':'2025-07-18 10:00:00'}]}]
            usserDataTask = [processUsertweetedTicker_Contract(userTweetData=userTweetData,timeframe=timeframe,simpleSearch=simpleSearch) for userTweetData in userData]
            results = await asyncio.gather(*usserDataTask)
            if not simpleSearch:
                userResult = await tickerCalled_AndScore(results)
                if userResult:
                    return userResult
            else:
                return results
        userResult = asyncio.run(main())
        return userResult
    except Exception as e:
        return {'Error': f'Error  Occured {e}'}
   

def SingleUserSearch(Handle:str,timeframe:str,tweet_limit:int=10):
    async def main():
        try:
            mode = 'singleSearch'
            timeframe_for_ai = '1,5,15,30,1:0,2:0,4:0,6:0,12:0,24:0'
           
            UserTweet = await RequestUserTweets(Handle,tweet_limit) # activate later
            
            userdata = asyncio.create_task(processUsertweetedTicker_Contract(UserTweet,timeframe,mode=mode,simpleSearch=True))
            userdata_for_Ai = asyncio.create_task( processUsertweetedTicker_Contract(UserTweet,timeframe_for_ai,mode=mode,simpleSearch=True))
            
            userdata =  await userdata
            userdata_for_Ai  = await userdata_for_Ai

            Ai_response = GeminiRefine(Ai_assits_Data=userdata_for_Ai)

            """ Set The Ai Response In Session To Be Used Later"""
            st.session_state['Ai_response'] = Ai_response
            
        except Exception as e:
            print(e)
            return {'Error':f'Unable To Process User Tweets!'}
       
        try:  
            logging.info('Reforming Data')  
                    
            displayObject = []
            username = list(userdata.keys())[0]
            tickerPriceInfo = userdata[username]

            for dateTickersiInfo in tickerPriceInfo:
                if dateTickersiInfo == None:
                    continue

                date = dateTickersiInfo[-2]['date_tweeted']
                followers = dateTickersiInfo[-1]['followers']
                for tickernInfo in dateTickersiInfo:
                    symbol = list(tickernInfo.keys())[0]
                    timeframeData  = list(tickernInfo.values())[0]
                    if not isinstance(timeframeData,list):
                        continue
                    
                    displayData = {
                        'Username':username,
                        'followers':followers,
                        'Date' :date,
                        'Symbol':symbol
                        
                    }
                    for priceData in timeframeData:
                       
                        displayData['Entry_Price'] = priceData['Entry_Price']
                        displayData[f"Price_{priceData['timeframe']}"] = priceData['Price']
                        displayData[f"{priceData['timeframe']}_%_Change"] = priceData['%_Change']
                        displayData[f"{priceData['timeframe']}_Peak_Price"] = priceData['Peak_Price']
                    displayObject.append(displayData)

            df = pd.DataFrame(displayObject)
            
            return df
        except Exception as e:
            return {'Error':f'Couldnt Display Data Due to {e}'}
             
    dataFrame = asyncio.run(main())
    if 'kolSearch' in st.session_state:
        del st.session_state['kolSearch']
    return(dataFrame)
             
def prepare_For_Ai(userdata):
    username = list(userdata.keys())[0]
    tickerPriceInfo = userdata[username]

    data_for_Ai_processing = {}
    count = 0
    for dateTickersiInfo in tickerPriceInfo:
        if dateTickersiInfo == None:
            continue

        for tickernInfo in dateTickersiInfo:
            symbol = list(tickernInfo.keys())[0]
            timeframeData  = list(tickernInfo.values())[0]
            if not isinstance(timeframeData,list):
                continue
            
            data_for_Ai_processing[f'{count}_{symbol}'] = {}
            for priceData in timeframeData:
                data_for_Ai_processing[f'{count}_{symbol}'][f"{priceData['timeframe']}"] = priceData['%_Change']
            count += 1
    return data_for_Ai_processing









