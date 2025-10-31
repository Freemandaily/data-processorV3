import time
import tweepy
import sys,requests
from datetime import datetime,timedelta
import datetime
import pytz,re
import json,os
import streamlit as st
import asyncio 
import aiohttp
import pandas as pd
import logging
import gspread
from gspread_dataframe import set_with_dataframe


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)


try:
    bearerToken =st.secrets['bearer_token']
except:
    bearerToken = os.environ.get('bearerToken')

RAPID_API_KEY  =  os.environ.get('RAPID_API_KEY')



class processor:
    def __init__(self) -> None: # Default 7 days TimeFrame
        self.client =  tweepy.Client(bearerToken)
        self.username = None
        self.user = None
        self.user_id = None
        self.timeframe = None
        self.end_date = None
        self.start_date = None
        self.tweets = None
        self.fill_contract = 0
        self.miss_contracts = 0
    
    def Load_user(self,username,timeframe=7):
        self.username = username
        self.timeframe = timeframe
        try:
            self.user =  self.client.get_user(username=username)
            self.user_id = self.user.data.id
            self.end_date = datetime.datetime.now(pytz.UTC).replace(microsecond=0)
            self.start_date =  (self.end_date - timedelta(days=timeframe)).replace(hour=0,minute=0,second=1,microsecond=0)
            st.toast(f'@{username} Handle Successfully Loaded')
            return {'Success':True}
        except Exception as e:
            time.sleep(2)
            Error_message = {'Error':f'Error: {e}\n.Upgrade Your X Developer Plan or Try Again later'} # handle error according to it error
            return Error_message
        
    def linkSearch(self,link:str,timeframe:str):
        url = 'https://basesearchv3-71083952794.europe-west3.run.app/link'
        # url = 'https://basesearchv3.onrender.com/link'
        # url = 'http://127.0.0.1:8000/link'
        params ={
            'tweet_url':link,
            'timeframe':timeframe
        }
        response = requests.get(url=url,params=params)
        if response.status_code == 200:
            data = response.json()
            return data
        return {'Error':f'Failed Search With Code {response.status_code}.module:TweetData.py'}

    def SearchTickerOnCex(self,tickers:str,start_date:str,timeframe:str) ->dict:
        logging.info('sending Requst For Cex Ticker Search')
        url = 'https://basesearchv3-71083952794.europe-west3.run.app/ticker'
        url = 'https://base-xhtw.onrender.com/ticker'
        # url = 'https://basesearchv3.onrender.com/ticker'
        # url = 'http://127.0.0.1:8000/ticker'
        params ={
            'tickers':tickers,
            'start_date':start_date,
            'timeframe':timeframe
        }
        response = requests.get(url=url,params=params)
        if response.status_code == 200:
            data = response.json()
            return data
        return {'Error':f'Failed Search With On Cex Code {response.status_code}.module:TweetData.py'}



    # Fetching Ticker and contracts contains in the tweet
    def fetchTicker_Contract(self,tweet_text:str) -> dict:
        logging.info('Fetching Tweeted Contract in the Tweet')
        contract_patterns = r'\b(0x[a-fA-F0-9]{40}|[1-9A-HJ-NP-Za-km-z]{32,44}|T[1-9A-HJ-NP-Za-km-z]{33})\b'
        ticker_partterns = r'\$[A-Za-z0-9_-]+'

        find_contracts = re.findall(contract_patterns,tweet_text)
        ticker_names = re.findall(ticker_partterns,tweet_text) 
        
        if 'ticker_onchain' in st.session_state:
            ticker_onchain = st.session_state['ticker_onchain']

            if 'matched_ticker_contracts' in st.session_state:
                # find_contracts = st.session_state['matched_ticker_contracts']
                find_tickers = list({symbol.upper()[1:] for  symbol in re.findall(r'\$[A-Za-z0-9_-]+',tweet_text) if symbol.upper()[1:] in list(map(str.upper,ticker_onchain))})

                if find_tickers:
                    find_contracts =  st.session_state['matched_ticker_contracts']
                   
                    self.fill_contract +=1
                else:
                    find_contracts = []
                    self.miss_contracts +=1
            else:
                pass

        token_details = {
            'ticker_names' : re.findall(ticker_partterns,tweet_text),
            'contracts' : find_contracts
        }
        if 'valid contracts' in st.session_state:
            contracts = [contract for contract in token_details['contracts'] if contract.upper() in st.session_state['valid contracts']]
            token_details['contracts'] = contracts
        return token_details


    def fetchTweets(self,username:str,tweet_limit:int):
        from datetime import datetime
        url = "https://twitter-api45.p.rapidapi.com/timeline.php"
        params = {
            'screenname':username,
            'cursor': ''
        }

        headers = {
            "x-rapidapi-key": RAPID_API_KEY,
            "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
        }

        user_tweets = []
        keep_fetching = True

        try:
            while keep_fetching:
                        
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    print(response.status_code)
                    result = response.json()

                    timeline = result['timeline']

                    if timeline:
                        for tweet in timeline:
                            created_at = tweet['created_at']
                            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                            tweet_date = dt.strftime("%Y-%m-%d %H:%M")

                            tweet_dict = {
                                'tweet_id':tweet['tweet_id'],
                                'tweet_text':tweet['text'],
                                'created_at':tweet_date,
                                'username':username
                            }
                            if len(user_tweets) >= tweet_limit:
                                keep_fetching = False
                                break
                            user_tweets.append(tweet_dict)
                    else:
                        logging.error('There is no tweet')

                    if result['next_cursor'] is not None and result['next_cursor'] != params['cursor']:
                        params['cursor'] = result['next_cursor'] 
                    else:
                        break
                else:
                    st.error('Couldnt Requuest For User Data')   

                self.tweets = user_tweets     
               
        except Exception as e:  
            logging.error(f'Failed To Fetch Tweets Wait For Sometimes')
            Error_message = {'Error':f'Failed To Fetch Tweets Because of  {e}\n Wait For Sometimes'}
            self.tweets = Error_message

    
    # Using X API to fetch user tweets
    # def fetchTweets(self,tweet_limit:int=10) -> list:
    #     logging.info('Fetching User Tweet(s)')
    #     if self.timeframe == 7:
    #         request_limit = 1
    #     else:
    #         request_limit = 1
    #     user_tweets = []
    #     try:
    #         for response in tweepy.Paginator(self.client.get_users_tweets,
    #                                         id=self.user_id,
    #                                         start_time=self.start_date, 
    #                                         end_time=self.end_date,
    #                                         exclude='replies',
    #                                         max_results=100,
    #                                         limit=request_limit, # consider this
    #                                         tweet_fields='created_at'):
                
    #             if response.data:
    #                 for tweet in response.data:
    #                     tweet_dict = {
    #                         'tweet_id':tweet.id,
    #                         'tweet_text':tweet.text,
    #                         'created_at':tweet.created_at.strftime("%Y-%m-%d %H:%M"),
    #                         'username': self.username
    #                     }

    #                     if len(user_tweets) >= tweet_limit:
    #                         break
    #                     user_tweets.append(tweet_dict)

    #         self.tweets = user_tweets
    #     except Exception as e:  
    #         logging.error(f'Failed To Fetch Tweets Wait For Sometimes')
    #         Error_message = {'Error':f'Failed To Fetch Tweets Because of  {e}\n Wait For Sometimes'}
    #         self.tweets = Error_message
       
    # format the data to a suitable data type
    def Reformat(self,fetched_Token_details:list) -> dict:
        details = {}
        for data in fetched_Token_details:
            if 'Search_tweets_Contract' in st.session_state:
                details[data['username']] = { 'Token_names': data['token_details']['ticker_names'],
                                       'contracts': data['token_details']['contracts'],
                                       'username':data['username'],
                                       'followers': data['followers'],
                                       'tweet_id':data['tweet_id'],
                                       'date':data['date']}
            else:
                details[data['date']] = { 'Token_names': data['token_details']['ticker_names'],
                                       'contracts': data['token_details']['contracts'],
                                       'username':data['username'],
                                       'date':data['date'],
                                       'tweet_id':data['tweet_id'],}
        details = {date: tokenName_contract for date,tokenName_contract in details.items() if tokenName_contract['Token_names'] or tokenName_contract['contracts']}
        
        if details:
            st.toast('Tweets Containing Token Symbols Found!')
            time.sleep(3)
            return details
        else:
            logging.error('No Tweets Contain Any Token Symbols Or CA.\nAdjust Timeframe and Try Again')
            Error_message = {'Error':'No Tweets Contain Any Token Symbols Or CA.\nAdjust Timeframe and Try Again'}
            time.sleep(7)
            return Error_message
        
    # Start procesing user tweet
    def processTweets(self)->dict: # Entry function
        logging.info('Processing Tweets')
        tweets = self.tweets
        
        if isinstance(tweets,dict) and 'Error' in tweets:
            return tweets # Error handling for streamlit
        elif tweets == None:
            st.error('There is no Tweet To Process. Try Again Please')
            return {'Error':'There is no Tweet To Process. Try Again Please'}
        fetched_Token_details = []
    
        if tweets:
            for tweet in tweets:
                token_details = self.fetchTicker_Contract(tweet['tweet_text'])
                if 'Search_tweets_Contract' in st.session_state:
                    refined_details = {
                    'username':tweet['username'],
                    'followers':tweet['followers'],
                    'tweet_id':tweet['tweet_id'],
                    'token_details': token_details,
                    'date': tweet['created_at']
                }
                else:   
                    refined_details = {
                        'username':tweet['username'],
                        'token_details': token_details,
                        'date': tweet['created_at'],
                        'tweet_id':tweet['tweet_id']
                    }
                fetched_Token_details.append(refined_details)
          
            tweeted_Token_details = self.Reformat(fetched_Token_details)
            if 'Search_tweets_Contract' not  in st.session_state:
                return tweeted_Token_details
            else:
                st.session_state['tweeted_token_details'] = tweeted_Token_details            
        else :
            Error_message = {'Error':f'Not Able To Process {self.username} Tweets! Please check I'}
            if 'Search_tweets_Contract' not  in st.session_state:
                return Error_message
            else:
                st.error('There is no Tweet To Process. Adjust To Lower Followers Threshold and Try Again')
                st.stop()
        
        
        
    # Get tweet id and user using the provided url
    def Fetch_Id_username_url(self,url):
        url = url.lower()
        if url.startswith('https://x.com/'):
            try:
                tweet_id = url.split('/')[-1]
                username = url.split('/')[-3]
                if len(tweet_id) == 19 and isinstance(int(tweet_id),int):
                    return tweet_id,username #this should update the self.username
                else:
                    raise ValueError('Incorrect Tweet Id')
            except ValueError as e:
                logging.error('Make Sure Url Contains Valid Tweet Id')
                st.error(f'Make Sure Url Contains Valid Tweet Id ')
                st.stop()
        else:
            logging.error('Provide A Valid X Url')
            st.error('Provide A Valid X Url')
            st.stop()

    def search_with_id(self,url):
        logging.info('Searching Tweet...')
        tweet_id,username =  self.Fetch_Id_username_url(url)
        try:
            tweets = self.client.get_tweets(tweet_id,tweet_fields=['created_at'])
            user_tweets = []
            for tweet in tweets.data:
                tweet_dict = {
                    'tweet_text':tweet.text,
                    'created_at':tweet.created_at.strftime("%Y-%m-%d %H:%M"),
                    'username': username,
                    'tweet_id':tweet.id
                    }
                user_tweets.append(tweet_dict)
            self.tweets = user_tweets
        except Exception as e:
            logging.error(f'Failed To Fetch Tweets  {e}')
            Error_message = {'Error':f'Failed To Fetch Tweets Because of  '} # this Error comes because of invali tweet id , configure correctly
            self.tweets = Error_message


class contractProcessor(processor):

    def __init__(self,mint_addresses:list,date_time=None):
        super().__init__() # to access processor attributes
        self.mint_addresses = mint_addresses # -> list
        self.pairs = []
        self.tokens_data = []
        self.date_time = date_time
        self.contracts_price_data = []
        self.from_timetamp = 0
        self.to_timestamp = 0
        self.matched_ticker_contracts = []
        
    
    async def Priceswharehouse(self,session,poolId):
        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        #     "Accept": "application/json"
        # }

        headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://www.geckoterminal.com/",  # Important: sometimes required
                "Origin": "https://www.geckoterminal.com",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }


        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
        #     "Accept": "application/json, text/plain, */*",
        #     "Accept-Encoding": "gzip, deflate, zstd",  # Removed 'br' to avoid Brotli
        #     "Accept-Language": "en-US,en;q=0.9",
        #     "Origin": "https://www.geckoterminal.com",
        #     "Referer": "https://www.geckoterminal.com/",
        #     "Sec-CH-UA": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        #     "Sec-CH-UA-Mobile": "?0",
        #     "Sec-CH-UA-Platform": '"Windows"',
        #     "Sec-Fetch-Dest": "empty",
        #     "Sec-Fetch-Mode": "cors",
        #     "Sec-Fetch-Site": "same-site",
        #     "Priority": "u=1, i"
        #     }
                
        url = f"https://app.geckoterminal.com/api/p1/candlesticks/{poolId}?resolution=1&from_timestamp={self.from_timetamp}&to_timestamp={self.to_timestamp}&for_update=false&currency=usd&is_inverted=false"
        
        try:
            async with session.get(url=url,headers=headers) as response:
                result = await response.json()
                datas = result['data']
                price_data = [value for data in datas for key in ['o','h','l','c'] for value in [data[key]]]
                dates = [value for data in datas for key in ['dt'] for value in [data[key]]]
                """
                This fetch get data from the gecko terminal website,
                so the time is in GMT which is lagging 1 hour . 
                Also i some candle are missing in some chart , 
                below code is used to mitigate it.
                i have to add 1 hour to  the time. 
                i only use the time to check if the candle chart start from the self.from_timestamp
                """
                from datetime import datetime,timedelta
                new_dates_timestamp = [ ]
                for date in dates:
                    dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    unix_timestamp = int(dt.timestamp())
                    new_dates_timestamp.append(unix_timestamp)
                
                return price_data,new_dates_timestamp
        except Exception as e:
            st.error("Cant Fetch Price")
            logging.error(f"Cant Fetch Price.Issue: {e}")

    async def fetch_ohlc_and_compute(self,session,poolId,network):
            logging.info('Fetching Token Prices With Timefrane')
            
            try:
                task_price  = asyncio.create_task(self.Priceswharehouse(session,poolId))
                price_data,new_date_timestamp = await task_price
                """
                This checks if the starting candle timestamp is there
                if the candle is there m  we take only the closing price and discard the candle
                else we keep the candle and start at the open price
                Rem, this is from website api , the data formation varies
                """
                if self.from_timetamp in new_date_timestamp:
                    entry_price = price_data[4]
                    price_data = price_data[4:]
                else:
                    entry_price = price_data[0]
                
                if self.to_timestamp in new_date_timestamp: # Some request gives extra timestamp, i handle it here
                    price_data = price_data[:-4]
                
                close_price = price_data[-1] 
                peak_price = round(max(price_data),7)
                lowest_price = round(min(price_data),7)
                max_so_far = price_data[0]
                max_drawdown  = 0 
                
                percentage_change = str(round(((close_price - entry_price)/entry_price) * 100,3)) + '%'
                entry_to_peak = str(round(((peak_price - entry_price) /entry_price) * 100,3)) +'%'
                entry_price = "{:.13f}".format(entry_price).rstrip("0") 
                close_price = "{:.13f}".format(close_price).rstrip("0")
                lowest_price =  "{:.13f}".format(lowest_price).rstrip("0")
                peak_price = "{:.13f}".format(peak_price).rstrip("0")

            except Exception as e:
                logging.error(f'Please Choose Timeframe Within Token Traded Price {e}')
                st.error(f"Please Choose Timeframe Within Token Traded Prices")
               
            try:
                for price in price_data:
                    if price > max_so_far :
                        max_so_far = price
                    drawadown = (( price - max_so_far) / max_so_far) * 100
                    max_drawdown = min(drawadown,max_drawdown)

                price_info = {'Entry_Price': entry_price, #round(entry_price,7),
                            'Price':close_price,#round(close_price,7),
                            '%_Change':percentage_change,
                            # DrawDown,
                            'Peak_Price':peak_price,
                            '%_Entry_to_Peak': entry_to_peak,
                            'lowest_Price' : lowest_price,
                            'Max_Drawdown': round(max_drawdown,7)
                            }
                return price_info
            except Exception as e:
                logging.error(f'Please Choose Timeframe Within Token Traded Pricess{e}')
                st.error(f"Please Choose Timeframe Within Token Traded Prices")

   
    async def gecko_price_fetch(self,session,timeframe,poolId,pair=None,network=None) -> dict:
        try:
            task1 = asyncio.create_task(self.fetch_ohlc_and_compute(session,poolId,network)) 
            time_frame_Task = await task1
            if int(timeframe) > 60:
                    hour = str(timeframe //60)
                    minutes = timeframe %60
                    
                    timeframe = f'{hour}:{minutes}m'  if minutes > 0  else f'{hour}hr(s)' 
            else:
                timeframe = f'{timeframe}m'

            pair_data_info = {pair:{ 
                f'{timeframe}': time_frame_Task
            }}
            return pair_data_info
        except Exception as e:
            st.error(f"Please Choose Timeframe Within Token Traded Prices")
            logging.error(f"Please Choose Timeframe Within Token Traded Prices{e}")

    def process_date_time(self,added_minute):
        from datetime import datetime
        combine = self.date_time
        added_minute = added_minute + 1
        time_object = datetime.strptime(str(combine), "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.FixedOffset(60))
        processed_date_time = time_object + timedelta(minutes=added_minute) # added 1 beacuse of how gecko terminal fetch price, price begin at the previou timestamp
        from_timestamp = time_object.timestamp()
        to_timestamp = processed_date_time.timestamp()
        self.from_timetamp = int(from_timestamp)
        self.to_timestamp = int(to_timestamp)

    async def main(self,timeframe): 
        async with aiohttp.ClientSession() as session:
            task_container = [self.gecko_price_fetch(session,timeframe,data['poolId'],pair=data['pair'],network=data['network_id']) for data in self.tokens_data]
            contracts_price_data = await asyncio.gather(*task_container)
            self.contracts_price_data = contracts_price_data
            
        for data in self.tokens_data:
            pair = data['pair']
            for element in self.contracts_price_data: # add element[pair][network] = data[network]
                try:
                    element[pair]['address'] = data['address']
                    element[pair]['symbol'] = data['symbol']
                    element[pair]['network'] = data['network_id']
                except:
                    pass
        
    def process_contracts(self,timeframe): 
        self.process_date_time(timeframe)
        asyncio.run(self.main(timeframe))
    
    async def Fetch_PoolId_TokenId(self,session,network_id,pair):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }

        # headers = {
        #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
        #         "Accept": "application/json",
        #         "Accept-Language": "en-US,en;q=0.5",
        #         "Accept-Encoding": "gzip, deflate",
        #         "Referer": "https://www.geckoterminal.com/",  # Important: sometimes required
        #         "Origin": "https://www.geckoterminal.com",
        #         "Connection": "keep-alive",
        #         "Sec-Fetch-Dest": "empty",
        #         "Sec-Fetch-Mode": "cors",
        #         "Sec-Fetch-Site": "same-origin"
        #     }

        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
        #     "Accept": "application/json, text/plain, */*",
        #     "Accept-Encoding": "gzip, deflate, zstd",  # Removed 'br' to avoid Brotli
        #     "Accept-Language": "en-US,en;q=0.9",
        #     "Origin": "https://www.geckoterminal.com",
        #     "Referer": "https://www.geckoterminal.com/",
        #     "Sec-CH-UA": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        #     "Sec-CH-UA-Mobile": "?0",
        #     "Sec-CH-UA-Platform": '"Windows"',
        #     "Sec-Fetch-Dest": "empty",
        #     "Sec-Fetch-Mode": "cors",
        #     "Sec-Fetch-Site": "same-site",
        #     "Priority": "u=1, i"
        #     }
        url = f"https://app.geckoterminal.com/api/p1/{network_id}/pools/{pair}?include=dex%2Cdex.network.explorers%2Cdex_link_services%2Cnetwork_link_services%2Cpairs%2Ctoken_link_services%2Ctokens.token_security_metric%2Ctokens.token_social_metric%2Ctokens.tags%2Cpool_locked_liquidities&base_token=0"
        async with session.get(url,headers=headers) as response:
           try:
                result = await response.json()
                data = result['data']
                poolId = data['id']
                pairId = result['data']['relationships']['pairs']['data'][0]['id']
                return poolId,pairId
           except Exception as e:
               st.error(f'Issue getting the poolId')
               logging.error(f'Issue getting the poolId{e}')

    async  def fetchNetworkId(self,session,address):
        # 
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
       
        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
        #     "Accept": "application/json",
        #     "Accept-Language": "en-US,en;q=0.5",
        #     "Accept-Encoding": "gzip, deflate",
        #     "Referer": "https://www.geckoterminal.com/",  # Important: sometimes required
        #     "Origin": "https://www.geckoterminal.com",
        #     "Connection": "keep-alive",
        #     "Sec-Fetch-Dest": "empty",
        #     "Sec-Fetch-Mode": "cors",
        #     "Sec-Fetch-Site": "same-origin"
        #     }

        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
        #     "Accept": "application/json, text/plain, */*",
        #     "Accept-Encoding": "gzip, deflate, zstd",  # Removed 'br' to avoid Brotli
        #     "Accept-Language": "en-US,en;q=0.9",
        #     "Origin": "https://www.geckoterminal.com",
        #     "Referer": "https://www.geckoterminal.com/",
        #     "Sec-CH-UA": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
        #     "Sec-CH-UA-Mobile": "?0",
        #     "Sec-CH-UA-Platform": '"Windows"',
        #     "Sec-Fetch-Dest": "empty",
        #     "Sec-Fetch-Mode": "cors",
        #     "Sec-Fetch-Site": "same-site",
        #     "Priority": "u=1, i"
        # }
        url = f'https://app.geckoterminal.com/api/p1/search?query={address}'
        async with session.get(url,headers=headers) as response:
            try:
                result = await response.json()
                data = result['data']['attributes']['pools'][0]
                pair = data['address']
                network_id = data['network']['identifier']
                tokens = data['tokens']
                for token in tokens: # used for fetching token symbol for redundancy
                    if token['is_base_token'] == True:
                        symbol = token['symbol']
                        break
                return network_id,pair,symbol
            except Exception as e:
                logging.error(f'Unable To Request For Contract Info From GeckoTerminal issue {e}')
                # st.error(f'Unable To Request For Contract Info From GeckoTerminal issue {e}')


    async def fetchtokenSupply(self,session,network_id,token_address):
            logging.info('Fetching For Token Supply')

            url = f"https://api.geckoterminal.com/api/v2/networks/{network_id}/tokens/{token_address}?include=top_pools"
            async with session.get(url) as response:
                results =  await response.json()
                data = results['data']['attributes']
                supply = data['normalized_total_supply']
                return supply

    # async def pair(self,session,address,pair_endpoint):
    async def pair(self,session,address):
        try:
            task_id = asyncio.create_task(self.fetchNetworkId(session,address))
            network_id,pair,symbol = await task_id
            pair_endpoint = f'https://api.geckoterminal.com/api/v2/networks/{network_id}/tokens/{address}/pools?include=base_token&page=1'
            async with session.get(pair_endpoint) as response:
                try:
                    result = await response.json()
                    if result['data']:
                        pair_address = result['data'][0]['attributes']['address']
                        symbol = result['data'][0]['attributes']['name']
                except:
                    pair_address = pair  
                    symbol = f"{symbol}/Token"

                task_poolId = asyncio.create_task(self.Fetch_PoolId_TokenId(session,network_id,pair_address))
                task_supply = asyncio.create_task(self.fetchtokenSupply(session,network_id,address))
                poolId,pairId = await task_poolId
                supply = await task_supply
                token_data = {'address':address,  #add 'network_id' = network_id
                            'pair':pair_address,
                            'symbol':symbol,
                            'network_id':network_id,
                            'poolId': f'{poolId}/{pairId}',
                            'supply':supply}
                self.pairs.append(pair_address)
                self.tokens_data.append(token_data)
                logging.info('Token Detail Added Successfully')
        except Exception as e:
            logging.error('Check If This Mint Address Is Correct: Unable to fetch Pair Info')
            # st.error(f'Check If This Mint Address Is Correct: Unable to fetch Pair Info{e}')
    
    async def pair_main(self):
        async with aiohttp.ClientSession() as session:  
            pairs_container = [self.pair(session,address) for address in self.mint_addresses]
            pairs = await asyncio.gather(*pairs_container)
            if 'Search_tweets_Contract' in st.session_state:
                st.session_state['tokens_data'] = self.tokens_data  # to be used by search coontract by twitter

    def fetch_pairs(self): 
        if 'data_frames' not in st.session_state: # so that slide dont refetch data again
            asyncio.run(self.pair_main())


    def pooldate(self):
        network_id = self.tokens_data[0]['network_id']
        contract = self.tokens_data[0]['address']
        url = f"https://api.geckoterminal.com/api/v2/networks/{network_id}/tokens/{contract}?include=top_pools"
        response = requests.get(url)
        if response.status_code != 200:
            st.error('Unabe To Fetch Pool Date')
            st.stop()
        results =  response.json()
        pooldata = results['included'][0]['attributes']
        pool_creation_date = pooldata['pool_created_at']
        return pool_creation_date
    
    def checkDuplicateUser(self,user_tweet,username,tweet_date):
        from datetime import datetime
        add = True
        try:
            for index,tweet in enumerate(user_tweet):
                if tweet['username'] == username and datetime.strptime(tweet['created_at'],"%Y-%m-%d %H:%M") > datetime.strptime(tweet_date,"%Y-%m-%d %H:%M"):
                    del user_tweet[index]
                    add = True
                    break
                elif tweet['username'] == username and datetime.strptime(tweet['created_at'],"%Y-%m-%d %H:%M") < datetime.strptime(tweet_date,"%Y-%m-%d %H:%M"):
                    add = False
                    break
                else:
                    add = True
        except Exception as e:
            add = True
        return user_tweet, add

    """ This matches The Ticker Searched With The Ticker gotten from geckoterminal search"""
    def _match_Ticker_Onchain(self):
        from datetime import datetime,timedelta

        if 'ticker_onchain' not in st.session_state:
            st.error('Error There Is No Ticker To Match Onchain')
            st.stop()
        
        ticker_onchain = self.mint_addresses
        

        for address in ticker_onchain:
            
            url = f'https://app.geckoterminal.com/api/p1/search?query={address[1:]}'
            headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
                            "Accept": "application/json",
                            "Accept-Language": "en-US,en;q=0.5",
                            "Accept-Encoding": "gzip, deflate",
                            "Referer": "https://www.geckoterminal.com/",  
                            "Origin": "https://www.geckoterminal.com",
                            "Connection": "keep-alive",
                            "Sec-Fetch-Dest": "empty",
                            "Sec-Fetch-Mode": "cors",
                            "Sec-Fetch-Site": "same-origin"
                        }
            response = requests.get(url=url,headers=headers)

            contracts = set()
            pool_date = set()
            if response.status_code == 200:
                result = response.json()
                
                if result:
                    pool_datas = result['data']['attributes']['pools']

                    for pool in pool_datas:
                        network = pool['network']['name']

                        pool_creation_date = datetime.strptime( pool['pool_creation_date'],"%Y-%m-%dT%H:%M:%SZ") #.replace(tzinfo=timezone.utc)
                        currrent_date = datetime.now()

                        if currrent_date - pool_creation_date > timedelta(days=7):
                            continue
                        else:
                            pool_date.add(pool['pool_creation_date'])
                            pass 

                        network_chosen = st.session_state['network_chosen']

                        if network.upper() != network_chosen.upper():
                            continue
                        
                        for token in pool['tokens']:
                            if token['is_base_token']:
                                token_address = token['address']
                                contracts.add(token_address)
            else:
                st.error(f'Error! Request To Match Ticker Onachain failed with status code: {response.status_code}')
                st.stop()

        if list(contracts):
            earliest_pool_date = min(list(pool_date))
            latest_pool_date = max(list(pool_date))
        else:
            st.error(f'There Is No Ticker On {st.session_state['network_chosen']} Created past 7days That Matches {ticker_onchain[0]} On GeckoTerminal Search')
            st.stop()

        st.session_state['matched_ticker_contracts'] = list(contracts)
        return  earliest_pool_date,ticker_onchain[0] # This Returns the Ticker 


    """ This Function Uses Rapid Api To Search for Ticker mention Onchain"""
    def _ticker_onchain(self,ticker:str,start_time:str,end_time:str):
        from datetime import datetime

        logging.info('Fetching Ticker Mentions On Twitter')
        conv_start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        conv_end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        start_time = conv_start_time.strftime("%Y-%m-%d_%H:%M:%S_UTC")
        end_time = conv_end_time.strftime("%Y-%m-%d_%H:%M:%S_UTC")


        url = "https://twitter-api45.p.rapidapi.com/search.php"
        params = {
            "query": f"${ticker} until:{end_time} since:{start_time}",
            'cursor': '',
            "search_type": "Top"
        }

        headers = {
            "x-rapidapi-key": RAPID_API_KEY,
            "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
        }
        
        users_tweet = [ ]
        while True:
                    
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                result = response.json()
                # with open('ticker_search.json','r') as file:
                #     result = json.load(file)

                
                time_line = result['timeline']

                if time_line:
                    for tweet in time_line:
                        if tweet['type'] == 'tweet':
                            created_at = tweet['created_at']
                            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                            tweet_date = dt.strftime("%Y-%m-%d %H:%M")

                            tweet_text = tweet['text']
                            tweet_id = tweet['tweet_id']
                            username = tweet['screen_name']
                            followers = tweet['user_info']['followers_count']

                            follower_threshold = st.session_state['follower_threshold']
                            if int(followers) < int(follower_threshold):
                                continue
                            users_tweet,affirm = self.checkDuplicateUser(users_tweet,username,tweet_date)
                            if affirm is True:
                                tweet_dict = {
                                        'tweet_text':tweet_text,
                                        'created_at':tweet_date,
                                        'username': username,
                                        'followers':followers,
                                        'tweet_id':tweet_id
                                        }
                                users_tweet.append(tweet_dict)
                else:
                    logging.error('There is no tweet')

                if result['next_cursor'] is not None and result['next_cursor'] != params['cursor']:
                    params['cursor'] = result['next_cursor'] 
                else:
                    break
            else:
                st.error('Couldnt Request To Fetch Ticker Mention On X')
        
        if users_tweet:
            self.tweets = users_tweet
            
            return {'success':'Yes'}
        else:
            return {'Error': f'There Is No Tweet Mentioning {ticker}'}


    def search_tweets_with_contract(self):
        from datetime import datetime,timedelta

        logging.info('Searching Tweets for Early Contract/Ticker Mentions')
        
        if 'ticker_onchain' in st.session_state:
            pool_creation_date,contract = self._match_Ticker_Onchain()
            # st.write(f'Pool Creation Date: {pool_creation_date}')
        else:
            contract = self.tokens_data[0]['address']
            pool_creation_date = self.pooldate()

        date = datetime.fromisoformat(pool_creation_date.replace('Z','+00:00'))

        first_tweet_minute = st.session_state['first_tweet_minute'] 
        new_date_pool_start = date + timedelta(minutes=first_tweet_minute) # Adjusted the starting time for the pool 1hr after to fetch price in geckoTerminal
        
        end_date_search = date + timedelta(hours=2)  # this is 2 hours after the pool was created
        start_time = new_date_pool_start.isoformat().replace('+00:00','Z')
        end_date = end_date_search.isoformat().replace('+00:00','Z')
        
        add_hour = 0
        while True:
            
            if 'ticker_onchain' in st.session_state:
                response = self._ticker_onchain(contract,start_time,end_date)
            else:
                response = self._recent_tweet_search(contract,start_time,end_date)

            if response != None and 'Error' in response:
                if add_hour >= 3:
                    break

                add_hour += 1
                dt = datetime.fromisoformat(end_date.replace('Z','+00:00'))
                dt += timedelta(hours=1)  # Adjusting end time by substrating an hour
                end_date = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                logging.info('Adding Hour to End Date For Another X Search')
            elif not isinstance(response,dict) and response.startswith("400 Bad Request"):
                
                line = response.splitlines()
                if len(line) >= 2:
                    invalid_text = line[1]

                    if invalid_text.startswith("Invalid 'end_time'"):
                        dt = datetime.fromisoformat(end_date.replace('Z','+00:00'))
                        dt -= timedelta(hours=1)  # Adjusting end time by substrating an hour
                        end_date = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                        
                        logging.info('Substrated An Hour to End Date For Another X Search')
                    else:
                        logging.error(f'Error: {invalid_text}')
                else:
                    logging.error(f'Error: {response}')
            elif not isinstance(response,dict) and  response.startswith("429 Too Many Requests"):
                st.error('Too Many Requests. Please Wait For A While')
                st.stop()
            else:
                break

    def _recent_tweet_search(self,contract,start_time,end_date):
        users_tweet = [ ]
        try:
            for response in tweepy.Paginator(self.client.search_recent_tweets,
                                    contract,
                                    start_time= str(start_time),  #pool_creation_date, 
                                    end_time= str(end_date),
                                    max_results=100,
                                    limit=6, # consider this (make 5 request)
                                    user_fields=['public_metrics','username'],
                                    tweet_fields=['author_id','created_at','public_metrics'],
                                    expansions=['author_id']):
                if response.data == None:
                    return {'Error':'No Tweet At This Date'}

                user_map = {user.id: user for user in response.includes.get('users', [])}
                for tweet in response.data:

                    tweet_date = tweet.created_at.strftime("%Y-%m-%d %H:%M")
                  
                    user = user_map.get(tweet.author_id)
                    if user: 
                        metrics = user.public_metrics
                        username = user.username
                        follower_count = metrics['followers_count']
                    else:
                        continue # Flter account with low followesr account Out
                    follower_threshold = st.session_state['follower_threshold']
                    if int(follower_count) < int(follower_threshold):
                        continue
                    users_tweet,affirm = self.checkDuplicateUser(users_tweet,username,tweet_date)
                    if affirm is True:
                        tweet_dict = {
                                'tweet_text':tweet.text,
                                'created_at':tweet_date,
                                'username': username,
                                'followers':follower_count,
                                'tweet_id':tweet.id
                                }
                        users_tweet.append(tweet_dict)
                    
            self.tweets = users_tweet
            logging.info(f'Fetched {len(users_tweet)} Tweets')
            return {'Success':'Added Tweets'}
        except Exception as e:
            logging.error(f'Fetching Tweets With Contract Failed {e}')
            return str(e)

    def NeededData(self,pricedata,timeframe):
        for key,value in pricedata.items():
            token_address = value['address']
            symbol = value['symbol'].split('/')[0]
            network = value['network']
            if 'token_price_info' not in st.session_state:
                st.session_state['token_price_info'] = {}

            if token_address not in st.session_state['token_price_info']:
                st.session_state['token_price_info'][token_address] = { 
                    'Info': ['Entry Price','Price','% Change','Peak Price','% Entry to Peak','lowest Price','Max Drawdown']
                }

            if int(timeframe) > 60:
                    hour = str(timeframe //60)
                    minutes = timeframe %60
                    
                    timeframe = f'{hour}:{minutes}m'  if minutes > 0  else f'{hour}hr(s)' 
            else:
                timeframe = f'{timeframe}m'  ;  
            st.session_state['token_price_info'][token_address][f'{timeframe}'] = [value[f'{timeframe}']['Entry_Price'],
                                                                                    value[f'{timeframe}']['Price'],
                                                                                    value[f'{timeframe}']['%_Change'],
                                                                                    value[f'{timeframe}']['Peak_Price'],
                                                                                    value[f'{timeframe}']['%_Entry_to_Peak'],
                                                                                    value[f'{timeframe}']['lowest_Price'],
                                                                                    value[f'{timeframe}']['Max_Drawdown']
                                                                                    ]
        data_frame = pd.DataFrame(st.session_state['token_price_info'][token_address])
        return data_frame,token_address,symbol,network

    def slide(self,price_datas:list,timeframe):
        if 'data_frames' not in st.session_state:
            st.session_state['data_frames'] = { }
            
        if 'address_symbol' not in st.session_state:
            st.session_state['address_symbol'] = []
        try:
            data_frames = []
            for pricedata in price_datas:
                data_frame,address,symbol,network = self.NeededData(pricedata,timeframe)
                address_sym = [address,symbol,network ]
                st.session_state['data_frames'][address] = data_frame
                st.session_state['address_symbol'].append(address_sym)
            if 'slide_index' not in st.session_state:
                st.session_state['slide_index'] = 0
            
            def next_slide():
                if st.session_state.slide_index < len(st.session_state['data_frames']) - 1:
                    st.session_state['slide_index'] +=1

            def prev_slide():
                if st.session_state.slide_index > 0:
                    st.session_state['slide_index'] -=1

            address = st.session_state['address_symbol'][st.session_state['slide_index']][0]
            st.badge(f"Token Address : {st.session_state['address_symbol'][st.session_state['slide_index']][0]}",color='violet')
            st.badge(f"Symbol : ${st.session_state['address_symbol'][st.session_state['slide_index']][1]}",color='orange')
            st.badge(f"Network : {st.session_state['address_symbol'][st.session_state['slide_index']][2]}",color='green')
            st.dataframe(st.session_state['data_frames'][address])
            logging.info('Displayed Data')

            col1,col2,col3 = st.columns([1,2,3])
            with col1:
                if st.button('Prev. CA',disabled=st.session_state['slide_index'] == 0):
                    prev_slide()
            with col2:
                if st.button('Next CA',disabled=st.session_state['slide_index'] == len(st.session_state['data_frames']) -1 ) :
                    
                    next_slide()
        except:
            logging.error('Session Ended: Analyze Data Again')
            st.error('Session Ended: Analyze Data Again. Check Your Input Fields')
            st.stop()
        
        col = st.columns([1,1])
        with col[0]:
            df_data = st.session_state['data_frames'][address]
            if st.button('Add To Sheet'):
                try:
                    gc = gspread.service_account(filename='freeman-461623-154dc403ca64.json')
                    spreadSheet = gc.open('TWEEET')
                    sheet = spreadSheet.worksheet('Sheet2')
                except:
                    st.error('Unable To Add Data To Sheet')
                    st.stop()
                last_row = len(sheet.get_all_values()) + 2
                set_with_dataframe(sheet, df_data, row=last_row, include_index=False, resize=True)
                st.toast( 'Succesfully Added Data To Sheet')






