import logging
import sys
import time,pytz
import requests,json
from datetime import datetime, timedelta
import asyncio,aiohttp
import streamlit as st
from TweetData import contractProcessor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

class price_with_interval:
    def __init__(self):
        self.token_interval_prices = []


def fetchPrice(network,pair,tweeted_date,timeframe,poolId): 
    async def Priceswharehouse(session,from_timestamp,to_timestamp,poolId):
        # headers = {
        #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        #     "Accept": "application/json"
        # }

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
        from_timestamp =  int(from_timestamp)
        to_timestamp = int(to_timestamp)
        retry_time = 5
        # time.sleep(4)
        for retry in range(retry_time):
            url = f'https://app.geckoterminal.com/api/p1/candlesticks/{poolId}?resolution=1&from_timestamp={from_timestamp}&to_timestamp={to_timestamp}&for_update=false&currency=usd&is_inverted=false'
           
            async with session.get(url=url,headers=headers) as response:
                if response.status !=200:
                    logging.warning(f"Fetching Price data with {url} Failed . Retrying for {retry} Times")
                    time.sleep(1)
                    continue
                result = await response.json()
                datas = result['data']
                price_data = [value for data in datas for key in ['o','h','l','c'] for value in [data[key]]]
                dates = [value for data in datas for key in ['dt'] for value in [data[key]]]

                """
                This fetch get data from the gecko terminal website,
                so the time is in GMT which is lagging 1 hour . 
                Also  some candle are missing in some chart , 
                below code is used to mitigate it. 
                i only use the time to check if the candle chart start from the self.from_timestamp
                """
                
                from datetime import datetime,timedelta
                new_dates_timestamp = [ ]
                for date in dates:
                    dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    unix_timestamp = int(dt.timestamp())
                    new_dates_timestamp.append(unix_timestamp)
                return price_data,new_dates_timestamp
        


    # async def fetch_ohlc_and_compute(session,endpoint_req) -> dict:
    async def fetch_ohlc_and_compute(session,network,from_timestamp,to_timestamp,timeframe,poolId) -> dict:
            try:
                task_price  = asyncio.create_task(Priceswharehouse(session,from_timestamp,to_timestamp,poolId))
                price_data,new_date_timestamp = await task_price
                if not price_data:
                    pass_check = []
                    return pass_check
                if int(from_timestamp) in new_date_timestamp:
                    open_price = price_data[4]
                    price_data = price_data[4:]
                else:
                    open_price = price_data[0]

                if int(to_timestamp) in new_date_timestamp:
                    price_data = price_data[:-4]

                close_price = price_data[-1]
                peak_price = max(price_data)
                lowest_price = min(price_data)
                max_so_far = price_data[0]
                max_drawdown  = 0
                entry_to_peak = str(round(((peak_price - open_price) /open_price) * 100,3)) +'%'
            except Exception as e:
                logging.error('This Token Hasnt Appeared On GeckoTerminal Api Yet AS AT Time Posted')
                # st.error(f'This Token Hasnt Appeared On GeckoTerminal Api Yet AS AT Time Posted {e}')
                pass_check = []
                return pass_check
            
            try:
                for price in price_data:
                    if price > max_so_far :
                        max_so_far = price
                    drawadown = (( price - max_so_far) / max_so_far) * 100
                    max_drawdown = min(drawadown,max_drawdown)
                price_info = {'open_price': open_price,
                            'close_price':close_price,
                            'lowest_price' : lowest_price,
                            'peak_price': peak_price,
                            'entry_to_peak':entry_to_peak,
                            'max_drawdown':str(round(max_drawdown,3)) +'%'
                            }
                return price_info
            except Exception as e:
                logging.error('This Token Hasnt Appeared On GeckoTerminal Api Yet AS AT Time Posted')
                # st.error(f'This Token Hasnt Appeared On GeckoTerminal Api Yet AS AT Time Posted{e}')
                # st.stop()
                pass_check = []
                return pass_check

    async def gecko_price_fetch(session,network,pair,from_timestamp,to_timestamp,timeframe,poolId):
        try:
            task1 = asyncio.create_task(fetch_ohlc_and_compute(session,network,from_timestamp,to_timestamp,timeframe,poolId))
            time_frame_Task = await task1
            if not time_frame_Task:
                pass_check = []
                return pass_check
            if int(timeframe) > 60:
                hour = str(timeframe //60)
                minutes = timeframe %60
                timeframe = f'{hour}:{minutes}m'  if minutes > 0  else f'{hour}hr(s)' 
            else:
                timeframe = f'{timeframe}m'
            pair_data_info = {pair:{
                f'{timeframe}' : time_frame_Task
            }}
            return pair_data_info
        except Exception as e:
            logging.error(f'Please Choose Timeframe Within Token Traded Prices')
            # st.error(f'Please Choose Timeframe Within Token Traded Prices')
            pass_check = []
            return pass_check
            

    def process_date_time(tweeted_date,added_minute):
        from datetime import datetime
        combine = tweeted_date
        added_minute = added_minute + 1
        time_object = datetime.strptime(str(combine), "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.FixedOffset(60))
        processed_date_time = time_object + timedelta(minutes=added_minute) # added 1 beacuse of how gecko terminal fetch price, price begin at the previou timestamp
        from_timestamp = time_object.timestamp()
        to_timestamp = processed_date_time.timestamp()
        return from_timestamp,to_timestamp

    
    # async def main(network,pair,timestamp,timeframe):
    async def main(network,pair,from_timestamp,to_timestamp,timeframe,poolId):
       
        async with aiohttp.ClientSession() as session:
            task_container = [gecko_price_fetch(session,network,pair,from_timestamp,to_timestamp,timeframe,poolId)]
            pair_price_data = await asyncio.gather(*task_container)
            pair_price_data = [price_data for price_data in pair_price_data if price_data]
            
            return pair_price_data

    # def process_pair(pair,tweeted_date,timeframe):
    def process_pair(network,pair,tweeted_date,timeframe,poolId):
        from_timestamp,to_timestamp = process_date_time(tweeted_date,timeframe)
        pair_price_data = asyncio.run(main(network,pair,from_timestamp,to_timestamp,timeframe,poolId))
        return pair_price_data
    price_timeframes = process_pair(network,pair,tweeted_date,timeframe,poolId)
    return price_timeframes   

def timeFrame(tweetDate,time_frame): # Computing  The Timeframe
    date_obj = datetime.strptime(tweetDate, "%Y-%m-%d %H:%M:%S")
    five_min_later = date_obj + timedelta(minutes=time_frame)
    minutes = five_min_later.minute
    seconds = five_min_later.second
    adjustment = timedelta(minutes=(5 - (minutes % 5)) if minutes % 5 > 2 else -(minutes % 5), 
                        seconds=-seconds)
    nearest_interval = five_min_later + adjustment
    time_frame_time = nearest_interval.strftime("%Y-%m-%d %H:%M:%S")
    return time_frame_time

def tweeted_timeframe(tweetDate): # Get the Rounding Time for Price Calculation
    date_obj = datetime.strptime(tweetDate, "%Y-%m-%d %H:%M:%S")
    minutes = date_obj.minute
    seconds = date_obj.second
    if minutes % 5 == 0 and seconds == 0:
        nearest_interval = date_obj
    else:
        minutes_past = minutes % 5
        seconds_total = minutes_past * 60 + seconds
        if seconds_total < 150:  # 2.5 minutes = 150 seconds
            adjustment = timedelta(minutes=-minutes_past, seconds=-seconds)
        else:
            adjustment = timedelta(minutes=(5 - minutes_past), seconds=-seconds)
        nearest_interval = date_obj + adjustment
    tweeted_time = nearest_interval.strftime("%Y-%m-%d %H:%M:%S")
    return tweeted_time

def percent_increase(initial_price:str,ending_price:str) -> str:
    try:
        percent = str(round(((ending_price - initial_price) /initial_price ) * 100,2))
        if not percent.startswith('-'):
            percent = percent + '%'
        else:
            percent = percent + '%'
        return percent
    except:
        return None

def fetchMessage():
    with st.spinner('Analyzing Token Prices. Please Wait....... '):
        time.sleep(3)



def format_number(supply,price):
    number  = float(supply)*float(price)

    if not isinstance(number, (int,float,str)):
        return str(number)
    
    abs_num = abs(float(number))
    if abs_num >= 1_000_000_000:
        return f"{abs_num/1_000_000_000:.1f}B"
    elif abs_num >= 1_000_000:
        return f"{abs_num/1_000_000:.1f}M"
    elif abs_num >= 1_000:
        return f"{abs_num/1_000:.1f}K"
    else:
        return f"{abs_num:.2f}"


def pooldate(network_id,contract,tweet_date):
    from datetime import datetime, timezone
    url = f"https://api.geckoterminal.com/api/v2/networks/{network_id}/tokens/{contract}?include=top_pools"
    time.sleep(2)
    response = requests.get(url)
    if response.status_code != 200:
        logging.error('Unable To Fetch Pool Date')
        # st.error('Unable To Fetch Pool Date')
        # st.stop()
        affirm = False
        return affirm
    results =  response.json()
    pooldata = results['included'][0]['attributes']
    pool_creation_date = pooldata['pool_created_at']

    pool_date = datetime.fromisoformat(pool_creation_date) 
    tweet_date = tweet_date.strftime("%Y-%m-%d %H:%M:%S")
    tweet_date = datetime.strptime(tweet_date, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    time_diff = tweet_date - pool_date
    first_tweet_minute = st.session_state['first_tweet_minute'] 
    time_diff_hours = time_diff.total_seconds() / int(first_tweet_minute) * 60 #2400  # 40 minute
    if time_diff_hours >= 1:
        affirm = True
    else:
        affirm = False
    return affirm

def scoring(timeframe,price_change):
    prototype  = {
                                'hour':{'100_percnt growth':4,   
                                    '50percnt growth':2,
                                    '20percnt growth':1}
      
                         }
    if price_change == None:
        score = 0
        return score
    else:
        if price_change[:1] == '-':
            score = 0
            return score
        
        price_change = float(price_change[:-1])

    def givescore(timeframe_score_board,timeframe,price_change,hour_minute):
        if timeframe >= list(timeframe_score_board.keys())[0]:
            for increase_perc,score in timeframe_score_board[hour_minute].items():
                if price_change >= increase_perc:
                    return score
                else:
                    score = 0
            return score
        else:
            score = 0
            return score

    hour_score = {
        4:{100:4,   
           50:2,
           20:1}
    }
    minutes_score = {
        15:{100:8,
           50:4,
           20:2}
    }
    if int(timeframe) >= 60:
        
        hour = int(timeframe //60)
        score = givescore(hour_score,hour,price_change,4)
        return score
    else:
        minutes = int(timeframe)
        score = givescore(minutes_score,minutes,price_change,15)
        return score
        

# Getting the different price timeframe 
def Tweet_tokenInfoProcessor(tweet_token_detail:dict,timeframe)->dict:
    logging.info('Fetching Price Of Tweeted Token')
    identifier = 0   
    structured_data = {}
    count = 0
    
    # with open('test_tweet.json', 'w') as file:
    #     datas = {'data':tweet_token_detail}
    #     json.dump(datas,file,indent=4)
    # st.stop()
    for date , token_fetched in tweet_token_detail.items():
        date_object = datetime.strptime(str(token_fetched['date']), "%Y-%m-%d %H:%M")
        date = date_object + timedelta(hours=1)
        # identity = token_fetched['username']
        identity = str(date)
       
        
        # structured_data[identifier] = {}
        token_symbol = [symbol[1:].upper() for symbol in token_fetched['Token_names']]
        token_contracts = [contract for contract in token_fetched['contracts']]

        username  = token_fetched['username']
       
        identity = identity + str(identifier)
        structured_data[identity] = { }
        if len(token_contracts) > 0:
            if 'tokens_data' not in st.session_state:
                process_contract = contractProcessor(token_contracts)
                if 'data_frames' in st.session_state: # delete session set by contract search option
                    del st.session_state['data_frames']
                    
                fetch_pairs = process_contract.fetch_pairs()
                tokens_data = process_contract.tokens_data
            else:
                if 'data_frames' in st.session_state: # delete session set by contract search option
                    del st.session_state['data_frames']
                tokens_data = st.session_state['tokens_data']

            for token_data in tokens_data:# token_contracts:
                pair_address = token_data['pair']
                token_address = token_data['address']
                symbol = token_data['symbol']
                network = token_data['network_id']

                identity = identity + str(identifier)
                structured_data[identity] = { }
                price_timeframes = fetchPrice(network,pair_address,date,timeframe,token_data['poolId'])

                if not price_timeframes:
                    logging.warning('Empty Price Data Spotted , Skipping')
                    identifier +=1
                    continue
                else:
                    # updating ids
                    identifier +=1

                
                if 'Search_tweets_Contract'in st.session_state:
                    structured_data[identity][token_address] = {'username': username,
                                                                'Followers': token_fetched['followers'],
                                                                'Tweet_id':token_fetched['tweet_id'],
                                                                'Tweet_Date':date,
                                                                'network':network,
                                                                'symbol': symbol.split('/')[0]
                                                                    }
                   
                else:
                    affirm = pooldate(network,token_address,date)
                    if affirm == False:
                        continue
                    structured_data[identity][token_address] = {'username': username,
                                                        'Tweet_Date':date,
                                                        'Tweet_id':token_fetched['tweet_id'],
                                                         'network':network,
                                                         'symbol': symbol.split('/')[0],# jupToken['symbol'],
                                                            }
                
                if int(timeframe) >= 60:
                    hour = str(timeframe //60)
                    minutes = timeframe %60
                    setTimeframe = f'{hour}:{minutes}m'  if minutes > 0  else f'{hour}hr(s)' 
                else:
                    setTimeframe = f'{timeframe}m'

                price_data = price_timeframes[0][pair_address]
                structured_data[identity][token_address]['Price_Tweeted_At'] = price_data[f'{setTimeframe}']['open_price'] #fetchPrice(pair_address,date,5,timeframe_prices,get_start_price='YES')
                structured_data[identity][token_address]['Market_Cap'] = format_number(token_data['supply'],price_data[f'{setTimeframe}']['open_price'])
                structured_data[identity][token_address][f'price_{setTimeframe}'] = price_data[f'{setTimeframe}']['close_price'] #fetchPrice(pair_address,date,5,timeframe_prices) # 5 min timeFrame
                percent_change = percent_increase(structured_data[identity][token_address]['Price_Tweeted_At'],structured_data[identity][token_address][f'price_{setTimeframe}'])
                structured_data[identity][token_address][f'price_{setTimeframe}%Increase'] = percent_change
                structured_data[identity][token_address][f'{setTimeframe}_lowest_price'] = price_data[f'{setTimeframe}']['lowest_price']
                structured_data[identity][token_address][f'{setTimeframe}_peak_price'] = price_data[f'{setTimeframe}']['peak_price']
                structured_data[identity][token_address][f'{setTimeframe}_entry_to_peak'] = price_data[f'{setTimeframe}']['entry_to_peak']
                entry_to_peak_percent_change = price_data[f'{setTimeframe}']['entry_to_peak']
                structured_data[identity][token_address][f'{setTimeframe}_Score'] = scoring(timeframe,entry_to_peak_percent_change)
                structured_data[identity][token_address][f'{setTimeframe} Drawdown'] = price_data[f'{setTimeframe}']['max_drawdown']

        count += 1     
    
    # st.write(f'empty coontracts: {count}')
    if 'valid contracts' in st.session_state:
        del st.session_state['valid contracts']
    
    structured_data= { date:value for date,value in structured_data.items() if value}
    if structured_data:
       if 'df_data' not in st.session_state:
        st.toast('Filtering  Fetched Token Price Data!')
        logging.info('Filtering  Fetched Token Price Data!')
       return structured_data
    else:
        logging.error('Error Fetching Token Price. CHeck If Token Is On GeckoTerminal Yet')
        Error_message = {'Error':'Empty Price Data'}
        return Error_message
    
# This fuunction fetches the tweeted contract proce data
def token_tweeted_analyzor(tweet_token_detail:dict,timeframe=5)-> dict: 
    # print(tweet_token_detail)
    logging.info('Fetching Tweeted Token Datas and Price TimeFrames Please Wait..')
    analyzor = Tweet_tokenInfoProcessor(tweet_token_detail,timeframe)
    if 'Error' in analyzor:
        return analyzor
    for username in analyzor: # filter
        analyzor[username] = {
            key : value for key,value in analyzor[username].items() if value['Price_Tweeted_At'] != None
        }
    return analyzor

# fetches token pairs seaching with token address (2)
def dexScreener_token_data(mint_address):
    url = f'https://api.dexscreener.com/latest/dex/tokens/{mint_address}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        token_data = data.get('pairs',[])
        pair = token_data[0]['pairAddress']
        return pair
    except requests.exceptions.ConnectionError:
        logging.error(f'Error :Failed to connect to {url}! App Executin Has Stopped!  Please Reload The Page')
        st.error(f'Error :Failed to connect to {url}! App Executin Has Stopped!  Please Reload The Page')
        st.stop()
    except requests.exceptions.Timeout:
        st.error(f"Error: Request timed out for{url}!. App Executin Has Stopped!  Please Reload The Page")
        st.stop()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error: A network-related error occurred! App Executin Has Stopped!  Please Reload The Page:")
        st.error(f"Error: A network-related error occurred! App Executin Has Stopped!  Please Reload The Page:")
        st.stop()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.error('Token Not Found')
        Error_message = {'Error':'Token Not Found'}
        return Error_message
    

def fetch_price(pair,tweeted_date,five_minute,ten_minute,fifteen_minute):
    
    async def fetch_ohlc_and_compute(session,endpoint_req) -> dict:
        try:
            async with session.get(endpoint_req) as response:
                
                response_data = await response.json()
                price_data = response_data['data']['attributes']['ohlcv_list']
                removable_index = [0,5]
                price_data = [price for subprice in price_data for index, price in enumerate(subprice) if index not in removable_index]
            
                open_price = price_data[-4]
                close_price = price_data[3]
                max_so_far = price_data[0]
                max_drawdown  = 0
                max_price = max(price_data)
                min_price = min(price_data)
                for price in price_data:
                    if price > max_so_far :
                        max_so_far = price
                    drawadown = (( price - max_so_far) / max_so_far) * 100
                    max_drawdown = min(drawadown,max_drawdown)
                
                price_info = {'open_price': open_price,
                            'close_price':close_price,
                            'max_drawdown':str(round(max_drawdown,3)) +'%'
                            }
                return price_info
        except:
            st.error('Gecko Rate Limited: Try Again')

    async def gecko_price_fetch(session,pair,five_timeframe_stamp,ten_timeframe_stamp,fifteen_timeframe_stamp) -> dict:
        try:
            task1 = asyncio.create_task(fetch_ohlc_and_compute(session,f'https://api.geckoterminal.com/api/v2/networks/solana/pools/{pair}/ohlcv/minute?aggregate=1&before_timestamp={int(five_timeframe_stamp)}&limit=5&currency=usd&token=base'))
            task2 = asyncio.create_task(fetch_ohlc_and_compute(session,f'https://api.geckoterminal.com/api/v2/networks/solana/pools/{pair}/ohlcv/minute?aggregate=1&before_timestamp={int(ten_timeframe_stamp)}&limit=10&currency=usd&token=base'))
            task3 = asyncio.create_task(fetch_ohlc_and_compute(session,f'https://api.geckoterminal.com/api/v2/networks/solana/pools/{pair}/ohlcv/minute?aggregate=1&before_timestamp={int(fifteen_timeframe_stamp)}&limit=15&currency=usd&token=base'))
            
            five_minutes_task = await task1
            ten_minutes_task = await task2
            fifteen_minutes_task = await task3
            
            pair_data_info = {pair:{ 
                '5m': five_minutes_task,
                '10m': ten_minutes_task,
                '15m': fifteen_minutes_task
            }}
            return pair_data_info
        except Exception as e:
            st.error(f'Gecko Rate Limited: Try Again')

    def process_date_time(tweeted_date,added_minute):
        from datetime import datetime
        combine = tweeted_date
        time_object = datetime.strptime(str(combine), "%Y-%m-%d %H:%M:%S")
        processed_date_time = time_object + timedelta(minutes=added_minute)
        added_date_time = processed_date_time.timestamp()
        return added_date_time # timestamp

    async def main(pair,five_timeframe_stamp,ten_timeframe_stamp,fifteen_timeframe_stamp):
        async with aiohttp.ClientSession() as session:
            task_container = [gecko_price_fetch(session,pair,five_timeframe_stamp,ten_timeframe_stamp,fifteen_timeframe_stamp)] #for pair in self.pairs]
            pair_price_data = await asyncio.gather(*task_container)
            return pair_price_data

    def process_pair(pair,tweeted_date,five_minute,ten_minute,fifteen_minute):
        five_timeframe_stamp = process_date_time(tweeted_date,five_minute)
        ten_timeframe_stamp = process_date_time(tweeted_date,ten_minute)
        fifteen_timeframe_stamp= process_date_time(tweeted_date,fifteen_minute)
        pair_price_data = asyncio.run(main(pair,five_timeframe_stamp,ten_timeframe_stamp,fifteen_timeframe_stamp))
        return pair_price_data

    price_timeframes = process_pair(pair,tweeted_date,five_minute,ten_minute,fifteen_minute)
    return price_timeframes



