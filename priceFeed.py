import sys
import time
import requests,json
from datetime import datetime, timedelta
from storage import add_to_csv


with open('key.json','r') as file:
    keys = json.load(file)
    moralis = keys['moralis']

class price_with_interval:
    def __init__(self):
        self.token_interval_prices = []

def fetchPrice(pair,tweetDate,time_frame,timeframe_prices,get_start_price=None): # accepts pair (3) get the price of the token ,
    from_date = tweetDate[:10]
    date_obj = datetime.strptime(from_date, '%Y-%m-%d')
    new_date = date_obj + timedelta(days=1)
    to_date = new_date.strftime('%Y-%m-%d')
    
    # DeAWLtRGAqCW7imV1jSC9NZkRKKGStFC1U7eDFBRxryR
    url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pair}/ohlcv?timeframe=5min&currency=usd&fromDate={from_date}&toDate={to_date}&limit=1000"

    headers = {
    "Accept": "application/json",
    "X-API-Key": f"{moralis}"
    }
    try:
        if not timeframe_prices.token_interval_prices:
            response = requests.request("GET", url, headers=headers)
            data = response.json()
            Token_Price_datas = data.get('result',[])
            timeframe_prices.token_interval_prices = Token_Price_datas
        else:
            Token_Price_datas = timeframe_prices.token_interval_prices

        for price_data in Token_Price_datas:
            moralis_date_obj = datetime.fromisoformat(price_data['timestamp'].replace('Z', '+00:00'))
            Moralis_formatted_date = moralis_date_obj.strftime("%Y-%m-%d %H:%M:%S")

            if get_start_price:
                time_frame_time = tweeted_timeframe(tweetDate)
            else:
                time_frame_time = timeFrame(tweetDate,time_frame)

            if Moralis_formatted_date == time_frame_time:
                open = price_data['open']
                high_price = price_data['high']
                low_price = price_data['low']
                close_price = price_data['close']
                return close_price

    except Exception as e:
        print(f'Failed To Fetch Token Price Data')
    


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
            percent = '+'+ percent + '%'
        else:
            percent = percent + '%'
        return percent
    except:
        return None



def Tweet_tokenInfoProcessor(jup_token_datas:dict,tweet_token_detail:dict): # Getting the different price timeframe 
    structured_data = {}
    for date , token_fetched in tweet_token_detail.items():
        structured_data[date] = {}

        token_symbol = [symbol[1:].upper() for symbol in token_fetched['Token_names']]
        token_contracts = [contract.upper() for contract in token_fetched['contracts']]
        for jupToken in jup_token_datas:
            try:
                if jupToken['symbol'].upper() in token_symbol:
                        print('Token With Same Symbol Found')
                        timeframe_prices = price_with_interval()
                        pair_address = dexScreener_token_data(jupToken['address']) # Call to get token pair address from dexscreener
                        structured_data[date][jupToken['address']] = {'pair':pair_address,
                                                                    'symbol':jupToken['symbol']} 
                        structured_data[date][jupToken['address']]['Price_Tweeted_At'] = fetchPrice(pair_address,date,5,timeframe_prices,get_start_price='YES')
                        structured_data[date][jupToken['address']]['price_5m'] = fetchPrice(pair_address,date,5,timeframe_prices) # 5 min timeFrame
                        structured_data[date][jupToken['address']]['price_10m'] = fetchPrice(pair_address,date,10,timeframe_prices) 
                        structured_data[date][jupToken['address']]['price_15m'] = fetchPrice(pair_address,date,15,timeframe_prices)
                        structured_data[date][jupToken['address']]['price_5m%Increase'] = percent_increase(structured_data[date][jupToken['address']]['Price_Tweeted_At'],structured_data[date][jupToken['address']]['price_5m'])
                        structured_data[date][jupToken['address']]['price_10m%Increase'] = percent_increase(structured_data[date][jupToken['address']]['Price_Tweeted_At'],structured_data[date][jupToken['address']]['price_10m'])
                        structured_data[date][jupToken['address']]['price_15m%Increase'] = percent_increase(structured_data[date][jupToken['address']]['Price_Tweeted_At'],structured_data[date][jupToken['address']]['price_15m'])
                        timeframe_prices.token_interval_prices = []
            except KeyboardInterrupt :
                print('Exiting Token Fetch')
        if len(token_contracts) > 0: # Simple checking for contracts list
           for jupToken in jup_token_datas:
                if jupToken['address'].upper() in token_contracts:
                    print('Contract found')
                    timeframe_prices = price_with_interval()
                    pair_address = dexScreener_token_data(jupToken['address']) # Call to get the pair address from dexscreener
                    structured_data[date][jupToken['address']] = {'pair':pair_address,
                                                              'symbol':jupToken['symbol']}
                    structured_data[date][jupToken['address']]['Price_Tweeted_At'] = fetchPrice(pair_address,date,5,timeframe_prices,get_start_price='YES')
                    structured_data[date][jupToken['address']]['price_5m'] = fetchPrice(pair_address,date,5,timeframe_prices)
                    structured_data[date][jupToken['address']]['price_10m'] = fetchPrice(pair_address,date,10,timeframe_prices) # 10 Minute Timeframe
                    structured_data[date][jupToken['address']]['price_15m'] = fetchPrice(pair_address,date,15,timeframe_prices)
                    structured_data[date][jupToken['address']]['price_5m%Increase'] = percent_increase(structured_data[date][jupToken['address']]['Price_Tweeted_At'],structured_data[date][jupToken['address']]['price_5m'])
                    structured_data[date][jupToken['address']]['price_10m%Increase'] = percent_increase(structured_data[date][jupToken['address']]['Price_Tweeted_At'],structured_data[date][jupToken['address']]['price_10m'])
                    structured_data[date][jupToken['address']]['price_15m%Increase'] = percent_increase(structured_data[date][jupToken['address']]['Price_Tweeted_At'],structured_data[date][jupToken['address']]['price_15m'])
                    timeframe_prices.token_interval_prices = []
    

    structured_data= { date:value for date,value in structured_data.items() if value}
    if structured_data:
        print('Filtering  Fetched Token Price Data!')
        time.sleep(2)
        return structured_data
    else:
        print('Unable To Fetch Tokens Prices Data\nPlease Check You Provider Usage eg Moralis!')
        sys.exit()
    

def token_tweeted_analyzor(tweet_token_detail:dict,influencer_username:str,strict_token='yes')-> dict: # This Function fetches token address searching with token symbols 
    
    print('Fetching Tweeted Token Datas and Price TimeFrames Please Wait..')
    try:
        if strict_token == 'yes':
            tokens_list_url = "https://token.jup.ag/strict"
        else:
            tokens_list_url = "https://token.jup.ag/all"
        

        response = requests.get(tokens_list_url) 
        status = response.status_code
        if status == 200:
            try:
                token_datas = response.json()
                analyzor = Tweet_tokenInfoProcessor(token_datas,tweet_token_detail)
    
                for date in analyzor: # filter
                    analyzor[date] = {
                        key : value for key,value in analyzor[date].items() if value['Price_Tweeted_At'] != None
                    }
                
                add_to_csv(Influencer_name=influencer_username,tweeted_token=analyzor)
            except json.JSONDecodeError:
                print("Error in Fetching Token List: Response is not valid JSON")
            except KeyError as e:
                print(f"Error in Fetching Token List:{e}")
            except TypeError as e:
                print(f"Error in Fetching Token List: {e}")
    except requests.exceptions.ConnectionError:
        print(f"Error: Failed to connect to the {strict_token}")
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out for{strict_token}")
    except requests.exceptions.RequestException as e:
        print(f"Error: A network-related error occurred: {e}")
    except KeyboardInterrupt:
        pass


def dexScreener_token_data(mint_address): # fetches token pairs seaching with token address (2)
    url = f'https://api.dexscreener.com/latest/dex/tokens/{mint_address}'
    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()
        token_data = data.get('pairs',[])
        pair = token_data[0]['pairAddress']
        return pair
    except requests.exceptions.ConnectionError:
        print(f'Error :Failed to connect to {url}')
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out for{url}")
    except requests.exceptions.RequestException as e:
        print(f"Error: A network-related error occurred: {e}")
    except Exception as e:
        pass




# data = {'2025-04-05 11:14:07': {'Token_names': ["$Ray","$sol"], 'contracts': []}, '2025-04-05 11:14:04': {'Token_names': ['$jup','$ray','$sol'], 'contracts': []}}
# token_tweeted_analyzor(data,'freeman','yes')