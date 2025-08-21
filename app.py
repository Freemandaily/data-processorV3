from datetime import datetime
import time
import pytz
import streamlit as st
import sys,logging
from TweetData import processor
from priceFeed import token_tweeted_analyzor
from storage import add_to_csv
from TweetData import contractProcessor
import gspread
from gspread_dataframe import set_with_dataframe
from KolSearch import searchKeyword,SingleUserSearch
from KolSearch import GeminiRefine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

class search_state():
    def __init__(self):
        self.search_with = None
search = search_state()

def worksForReload(contracts_input,
                   choose_time,
                   choose_date,
                   first_tweet_minute,
                   follower_threshold,
                   username_url,
                   kolSearch,
                   kolSearch_date,
                   kolSearch_From_date):
    
   
    try:
        if st.session_state['contracts_input'] != contracts_input:
            try: 
                if 'Search_tweets_Contract' in st.session_state: 
                    del st.session_state['Search_tweets_Contract']
                
                if 'ticker_onchain' in st.session_state:
                    del st.session_state['ticker_onchain']

                if 'Search_tweets_Contract_displayed' in st.session_state :
                    del st.session_state['Search_tweets_Contract_displayed']
                
                if 'Influencer_data' in st.session_state:
                    del st.session_state['Influencer_data'] 
                
                if 'df_data'in st.session_state:
                    del st.session_state['df_data']

                if 'data_frames' in st.session_state:
                    del st.session_state['data_frames']
                    del st.session_state['address_symbol']
                    del st.session_state['token_price_info'] 
                if 'linkSearch' in st.session_state:
                    del  st.session_state['linkSearch']
                if 'Search Ticker On Cex' in st.session_state:
                    del st.session_state['Search Ticker On Cex']
                
            except:
                pass
    except:
        pass
    
    try:
        if st.session_state['choose_time'] != choose_time and st.session_state['choose_time'] != None:
            try: 
                if 'data_frames' in st.session_state:
                    del st.session_state['data_frames']
                    del st.session_state['address_symbol']
                    del st.session_state['token_price_info']  
            except:
                pass
    except:
        pass
    
    try:
        if st.session_state['choose_date'] != choose_date and  st.session_state['choose_date'] != None:
            try: 
                if 'data_frames' in st.session_state:
                    del st.session_state['data_frames']
                    del st.session_state['address_symbol']
                    del st.session_state['token_price_info']  
            except:
                pass
    except:
        pass
    
    try:
        if st.session_state['first_tweet_minute'] != first_tweet_minute:
            if 'Search_tweets_Contract_displayed' in st.session_state :
                del st.session_state['Search_tweets_Contract_displayed']
    except:
        pass

    try:
        if st.session_state['follower_threshold'] != follower_threshold:
            if 'Search_tweets_Contract_displayed' in st.session_state :
                del st.session_state['Search_tweets_Contract_displayed']
        pass
    except:
        pass

    try:
        if st.session_state['kolSearch'] != kolSearch:
            if 'kolSearch_date' in st.session_state:
                del st.session_state['kolSearch_date']
    except:
        pass
    
    try:
        if st.session_state['kolSearch_date']  != str(kolSearch_date) and 'SingleSearch' not in st.session_state:
            
            if 'df_data'in st.session_state:
                    del st.session_state['df_data']
           
    except:
        pass
        

st.header('Data-Extraction and Processing')
with st.sidebar:
    st.title('Data Configuration')
    username_url = st.text_input('Enter X Handle Or Tweet Url (Https://..\n')
    timeframe = st.selectbox('Choose A TimeFrame',[7,30,90])
    tweet_limit = st.slider('Total Tweets To Analyze',1,60,1)
    first_tweet_minute = 20 # st.slider('First Tweet Minute After Pool Creation',1,60,1) # GeckoTerminal price indexing changes somethings we use this to toggle price searhc time
    follower_threshold =  st.slider('Kols Followers Threshold',1,1000,1000)
    st.divider()
    contracts_input = st.text_area('Enter Contracts/Ticker Names',placeholder='4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R\n7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr\nBTC\nETH')
    choose_date = st.date_input(label='Set A Date',value='today')
    choose_time = st.time_input('Set Time',value=None,step=300)
    st.divider()
    st.subheader('Performance Search')
    kolSearch = st.text_area('Enter Keywords To Search',placeholder='Enter A Market Moving News Here')
    kolSearch_date = st.date_input(label='Set A Date(Mandatory)',value='today')
    KolSearch_time = st.toggle('Add time')
    if KolSearch_time:
        set_time = st.time_input('Search Time',value=None,step=300)
    kolSearch_From_date = st.date_input(label='From date(Optional)',value=None)
    
    worksForReload(contracts_input,
                   choose_time,choose_date,
                   first_tweet_minute,
                   follower_threshold,
                   username_url,
                   kolSearch,
                   kolSearch_date,
                   kolSearch_From_date)

st.image('data-extract.png')
def loadsearch(process=None,timeframe=None):
    
    from datetime import datetime
    logging.info('Loading Search')
    if search.search_with == 'handle_Contract_Search':
        st.session_state['username_url'] = username_url
    
        logging.info(f'Search Contract From X Data Activated For @{username_url}')

        with st.spinner(f'Loading @{username_url} Handle'):
            userHandler = process.Load_user(username_url,timeframe=timeframe) 
            if 'Error' in userHandler:
                st.error(userHandler['Error'])
                st.stop() 
        
        with st.spinner(f'Processing @{username_url} Tweets'):
            global tweet_limit

            st.session_state['For_Ai'] = 'For_Ai' # To indicate that Ai Analysis is needed

            process.fetchTweets(username=username_url,tweet_limit=tweet_limit)
            tweeted_token_details = process.processTweets() # For processing  through tweet to find contract Mentinons
            if 'Error' in tweeted_token_details:
                st.stop()
            return tweeted_token_details
    elif search.search_with == 'handle_Cex_Search':
        with st.spinner(f'Processing @{username_url} Tweets'):
                if 'prepare_for_AI' in st.session_state:
                    del st.session_state['prepare_for_AI']
                if 'For_Ai' in st.session_state:
                    del st.session_state['For_Ai']
            
                timeframe = '1,5,15,4:0,24:0'
                st.session_state['Timeframe'] = timeframe
                # tweet_limit = 20
                data_frame = SingleUserSearch(username_url,timeframe,tweet_limit)
                st.session_state['SingleSearch'] = 'yes'
                if 'linkSearch' in st.session_state :
                    del st.session_state['linkSearch']
                return data_frame
    elif search.search_with == 'link':
        logging.info('Searching With Link')
        with st.spinner(f'Processing  Tweets in Url......'):
            timeframe = '1,15,4:0,24:0'
            st.session_state['Timeframe'] = timeframe

            tweeted_token_details = process.linkSearch(username_url,timeframe)
            st.session_state['linkSearch'] = username_url
            st.session_state['username_url'] = username_url
            return tweeted_token_details
    elif search.search_with == 'Contracts':
        search_option = st.selectbox(
            'Specify How To Search For The Contract',
            ('Search Ticker On Cex','Search Contracts Onchain','Search Contract From X Data','Search Ticker From X Data'),
            index=None,
            placeholder='Choose Search Option'
            )
        if search_option == 'Search Contract From X Data':
            logging.info('Search Contract From X Data Activated')
            st.session_state['Search_tweets_Contract'] = 'Search_tweets_Contract'

            if 'ticker_onchain' in st.session_state:
                del st.session_state['ticker_onchain']

            if 'data_frames' in st.session_state:
                del st.session_state['data_frames']

            combine_date_time = None  
        elif search_option == 'Search Ticker From X Data':
            logging.info('Search Ticker From X Data Activated')
            st.session_state['Search_tweets_Contract'] = 'Search_tweets_Contract'

            network_choice = st.selectbox(
                'Select Network Ticker Network',
                ('Solana','Ethereum','Arbitrum','Aptos','Ton','Base'),
                index=None,
                placeholder='Choose Network'
            )

            if network_choice:
                st.session_state['network_chosen'] = network_choice
            
                text_inputs  = contracts_input.split('\n')
                ticker_onchain = [text.strip() for text in text_inputs if text.strip() != '']
                st.session_state['ticker_onchain'] = ticker_onchain

                if 'data_frames' in st.session_state:
                    del st.session_state['data_frames']
                combine_date_time = None  
            else:
                st.error('Please Select Network')
                st.stop()
        elif search_option == 'Search Contracts Onchain':
            logging.info('Search Contracts Onchain Activated')
            if 'Search_tweets_Contract' in st.session_state: # delete the sessin set to indentify the contract search from x data
                del st.session_state['Search_tweets_Contract']
            
            if 'ticker_onchain' in st.session_state:
                del st.session_state['ticker_onchain']
            
            if 'df_data' in st.session_state:
                del st.session_state['df_data']
          
            if choose_date and choose_time:
                st.session_state['choose_date'] = choose_date
                st.session_state['choose_time'] = choose_time
                combine_date_time =  datetime.combine(choose_date,choose_time)
            else:
                st.error('Please Choose Date And Time')
                st.stop()
        elif search_option == 'Search Ticker On Cex':
            logging.info('Search Ticker On Cex Activated')

            if 'ticker_onchain' in st.session_state:
                del st.session_state['ticker_onchain']
            
            if 'Search Ticker On Cex' in st.session_state:
                return None
            if choose_date and choose_time:
                st.session_state['choose_date'] = choose_date
                st.session_state['choose_time'] = choose_time
                combine_date_time =  datetime.combine(choose_date,choose_time)
                with st.spinner(f'Processing  Search Ticker On Cex......'):
                    timeframe = '1,5,15,4:0,24:0'
                    st.session_state['Timeframe'] = timeframe
                    tickers = contracts_input
                    start_date = str(combine_date_time)
                    tweeted_token_details = process.SearchTickerOnCex(tickers,start_date,timeframe)
                    st.session_state['linkSearch'] = tickers
                    st.session_state['Search Ticker On Cex'] = 'yes'
                    st.session_state['contracts_input'] = contracts_input
                    if 'kolSearch' in st.session_state:
                        del st.session_state['kolSearch']

                    if 'Error' in tweeted_token_details:
                        st.error(tweeted_token_details['Error'])
                        st.stop()
                    else:
                        st.toast(f'{search.search_with} Tweets Successfully Processed!')    
                    # st.session_state['tweeted_token_details'] = tweeted_token_details
                    st.session_state['df_data'] = tweeted_token_details
                    return tweeted_token_details
            else:
                st.error('Please Choose Date And Time')
                st.stop()

        if search_option:
            if 'data_frames' not in st.session_state:
                with st.spinner(f'Loading  Contract(s)......'):
                    time.sleep(2)
                    text_inputs  = contracts_input.split('\n')
                    if 'ticker_onchain' in st.session_state:
                        contracts = [ f'{text.strip()}' for text in text_inputs if text.strip() != '']
                    else:
                        contracts = [text for text in text_inputs if not text.startswith('0x') or len(text) >= 32]
                    
                    if contracts:
                        st.session_state['contracts_input'] = contracts_input # this work with workforload function to enable seamless reload of pge
                        process = contractProcessor(contracts,combine_date_time)
                        st.session_state['process'] = process # to be used when rerun
                    else:
                        st.error('Please Enter Only  Token Contract/Ticker') 
                        st.stop()   
                    return process
            else:
                process = st.session_state['process']
                return process
        else:
            st.stop()

if len(username_url) > 0 and len(contracts_input) > 0 and len(kolSearch) > 0 :
    
    search_option = st.selectbox(
        'Multiple Search Input Detected Choose How To Search',
        ('Search Only With X handle/Url','Search With Contracts/Ticker Name','KolSearch_News'),
        index=None,
        placeholder='Choose Search Option'
        )
    if search_option == 'Search Only With X handle/Url':
        logging.info('Search Only With X handle/Url Selected')
        username_url = username_url.upper()
        if username_url.startswith('HTTP'):
            search.search_with = 'link'
        else:
            search.search_with = 'handle'
    elif search_option == 'Search With Contracts/Ticker Name':
        logging.info('Search With Contracts/Ticker Name')
        search.search_with = 'Contracts'
    elif search_option == 'KolSearch_News':
        logging.info('KolSearch_News')
        search.search_with = 'KolSearch'
elif len(username_url) > 0 and len(contracts_input) > 0:
    
    search_option = st.selectbox(
        'Multiple Search Input Detected Choose How To Search',
        ('Search Only With X handle/Url','Search With Contracts/Ticker Name'),
        index=None,
        placeholder='Choose Search Option'
        )
    if search_option == 'Search Only With X handle/Url':
        logging.info('Search Only With X handle/Url Selected')
        username_url = username_url.upper()
        if username_url.startswith('HTTP'):
            search.search_with = 'link'
        else:
            search.search_with = 'handle'
    elif search_option == 'Search With Contracts/Ticker Name':
        logging.info('Search With Contracts/Ticker Name')
        search.search_with = 'Contracts'
elif len(username_url) > 0 and  len(kolSearch) > 0 :
      
    search_option = st.selectbox(
        'Multiple Search Input Detected Choose How To Search',
        ('Search Only With X handle/Url','KolSearch_News'),
        index=None,
        placeholder='Choose Search Option'
        )
    if search_option == 'Search Only With X handle/Url':
        logging.info('Search Only With X handle/Url Selected')
        username_url = username_url.upper()
        if username_url.startswith('HTTP'):
            search.search_with = 'link'
        else:
            search.search_with = 'handle'
    elif search_option == 'KolSearch_News':
        logging.info('KolSearch_News')
        search.search_with = 'KolSearch'
elif len(contracts_input) > 0 and len(kolSearch) > 0 :
    
    search_option = st.selectbox(
        'Multiple Search Input Detected Choose How To Search',
        ('Search With Contracts/Ticker Name','KolSearch_News'),
        index=None,
        placeholder='Choose Search Option'
        )
    if search_option == 'Search With Contracts/Ticker Name':
        logging.info('Search With Contracts/Ticker Name')
        search.search_with = 'Contracts'
    elif search_option == 'KolSearch_News':
        logging.info('KolSearch_News')
        search.search_with = 'KolSearch'
elif len(username_url) > 0 and len(contracts_input) == 0:
    username_url = username_url.upper()
    if username_url.startswith('HTTP'):
        search.search_with = 'link'
    else:
        search.search_with = 'handle'
elif len(contracts_input) > 0 and len(username_url) == 0 and len(kolSearch) == 0 :
    search.search_with = 'Contracts'
elif len(kolSearch) > 0 and len(username_url) == 0 and len(contracts_input) == 0:
    logging.info('KolSearch_News')
    search.search_with = 'KolSearch'
elif len(kolSearch) > 0 and len(contracts_input) == 0:
    logging.info('KolSearch_News')
    search.search_with = 'KolSearch'
elif len(kolSearch) > 0 and len(username_url) == 0 :
    logging.info('KolSearch_News')
    search.search_with = 'KolSearch'
else:
    st.error('Please Enter Where To Search From')
    st.stop()


if search.search_with == 'handle' or  search.search_with == 'link':

    if search.search_with == 'handle':
        search_option = st.selectbox(
                f'How Do You Want To Search @{username_url} Tweets?',
                ('Search CEX Ticker From X Data','Search Contract From X Data'),
                index=None,
                placeholder='Choose Search Option'
                )
        
        if search_option == 'Search CEX Ticker From X Data':
            search.search_with = 'handle_Cex_Search'
        elif search_option == 'Search Contract From X Data':
            search.search_with = 'handle_Contract_Search'
        else:
            st.stop()
        
    st.session_state['first_tweet_minute'] = int(first_tweet_minute)
    st.session_state['follower_threshold'] = follower_threshold
    if 'SingleSearch_Display' not in st.session_state:
        if st.button('Analyse'):
            logging.info('Started Analyzing..')
            if 'Search Ticker On Cex' in st.session_state:
                del st.session_state['Search Ticker On Cex']
            if 'tokens_data' in st.session_state:
                del st.session_state['tokens_data']
            if 'Search_tweets_Contract' in st.session_state: # delete the sessin set to indentify the contract search from x data
                    del st.session_state['Search_tweets_Contract']

            if 'df_data' in st.session_state:
                del st.session_state['df_data']

            if 'Influencer_data' in st.session_state:
                del st.session_state['Influencer_data'] 

            process = processor()
            tweeted_token_details = loadsearch(process,timeframe)
            if 'Error' in tweeted_token_details:
                st.error(tweeted_token_details['Error'])
                st.stop()
            else:
                st.toast(f'{search.search_with} Tweets Successfully Processed!')    
            st.session_state['tweeted_token_details'] = tweeted_token_details # setting this so that for custom timeframe uses it

            if 'linkSearch' not  in st.session_state and 'SingleSearch' not in st.session_state:
                with st.spinner('Fetching Tweeted Tokens and Price Datas. Please Wait.....'):
                    analyzor = token_tweeted_analyzor(tweeted_token_details) # Removed Token choice
                    st.session_state['Timeframe'] = 5
                if 'Error' in analyzor:
                    st.error(analyzor['Error'])
                    st.stop()
        
                with st.spinner('Storing Tweeted Token(s) Data'):
                    df_data = add_to_csv(analyzor)  # Adding the tweeted token to cs file
                if 'Error' in df_data:
                    st.error(df_data['Error'])
                    st.stop()
                st.success( 'Succesfully Analyzed Tweeted Token(s)',icon="✅")
                time.sleep(1)
                st.session_state['df_data'] = df_data
            else:
                # Link Search
                st.session_state['df_data'] = tweeted_token_details
    
elif search.search_with == 'Contracts':

    if 'prepare_for_AI' in st.session_state:
        del st.session_state['prepare_for_AI']
    if 'For_Ai' in st.session_state:
        del st.session_state['For_Ai']
    if 'SingleSearch' in st.session_state:
        del st.session_state['SingleSearch']

    st.session_state['first_tweet_minute'] = int(first_tweet_minute)
    st.session_state['follower_threshold'] = follower_threshold
    process_2 = processor()
    process = loadsearch(process_2)

    if 'linkSearch' not in st.session_state and 'Search Ticker On Cex' not in st.session_state:
        if 'data_frames' in st.session_state:
            if st.button('Changed Input?:Rerun'):
                if 'data_frames' in st.session_state:
                    del st.session_state['data_frames']
                    del st.session_state['address_symbol']
                    del st.session_state['token_price_info']
        
        if 'ticker_onchain' not in st.session_state:
            process.fetch_pairs()

        if 'Search_tweets_Contract' not in st.session_state :
            next_timeframe = st.selectbox(
                'Add Timeframe',
                (5,10,15,30),
                #index=None,
                placeholder= 'Select Timeframe',
                accept_new_options=True
            )
        
            if  next_timeframe !=None:
                if isinstance(next_timeframe,str):
                    try:
                        hour_minute = next_timeframe.split(':')
                        hours_into_minutes = int(hour_minute[0]) 
                        minute = int(hour_minute[1])
                        next_timeframe = ( hours_into_minutes * 60) + minute
                    except:
                        try:
                            next_timeframe = int(next_timeframe)
                        except:
                            st.error('Please Select Valid Timeframe')
                            st.stop()
            
        if 'Search_tweets_Contract' in st.session_state and  'Search_tweets_Contract_displayed' not in st.session_state :
            with st.spinner('Searching Early Tweets Containing Contract.Might Take A While........'):
                process.search_tweets_with_contract()
                pass
            result= process.processTweets()


            if result != None and  'Error' in result:
                st.stop()
            with st.spinner('Fetching Tweeted Contract Price Datas. Please Wait.....'):
                tweeted_Token_details = st.session_state['tweeted_token_details'] 
                analyzor = token_tweeted_analyzor(tweeted_Token_details,5)
                st.session_state['Timeframe'] = 5

                if 'Error' in analyzor:
                    st.error(analyzor['Error'])
                    st.stop()

                with st.spinner('Storing Tweeted Token(s) Datas'):
                    df_data = add_to_csv(analyzor)  
                if 'Error' in df_data:
                    st.error(df_data['Error'])
                    st.stop()
                st.success( 'Succesfully Analyzed Tweeted Token(s)',icon="✅")
                time.sleep(1)
                st.session_state['df_data'] = df_data
        elif 'Search_tweets_Contract' not  in st.session_state :
            process.process_contracts(next_timeframe)
            price_datas = process.contracts_price_data
            process.slide(price_datas,next_timeframe)
elif search.search_with == 'KolSearch':
    
    if 'prepare_for_AI' in st.session_state:
        del st.session_state['prepare_for_AI']
    if 'For_Ai' in st.session_state:
        del st.session_state['For_Ai']
    if 'SingleSearch_Display' in st.session_state:
        del st.session_state['SingleSearch_Display']
    if 'SingleSearch' in st.session_state:
        del st.session_state['SingleSearch']
    if 'linkSearch' in st.session_state :
        del st.session_state['linkSearch']
    timeframe = '1,2,3' #'5,20,30,1:0,2:0'
    TotalUsersToRetrieve = 5
    AnalyzeTweet =  10
    
    if kolSearch_date and 'displayed' not in st.session_state: #and 'kolSearch' not in st.session_state:
        st.session_state['kolSearch'] =  kolSearch
        st.session_state['kolSearch_date'] = str(kolSearch_date)
        st.session_state['Timeframe'] = timeframe
        with st.spinner(f'Searching Early Tweets On {kolSearch} And Analyzing Account Involves. Please Wait ......'):
            if KolSearch_time:
                search_time = set_time
            else:
                search_time = None
            if kolSearch_From_date:
                
                kolSearch_From_date= str(kolSearch_From_date)
            else:
                kolSearch_From_date = None
            userResult = searchKeyword(
                keyword=kolSearch,
                date=str(kolSearch_date),
                timeframe=timeframe,
                from_date=kolSearch_From_date,
                time=search_time,
                limit= TotalUsersToRetrieve,
                userTweetLimit=AnalyzeTweet,
                followers_threshold= int(follower_threshold)
                )
        if 'Error' in userResult:
            st.error(userResult['Error'])
            st.stop()
        st.session_state['df_data'] = userResult

def display(df_data):
    
    from datetime import datetime
    next_timeframe = st.selectbox(
        'Add Timeframe for x',
        (5,10,15,30),
        index=None,
        placeholder= 'Select Timeframe for x',
        accept_new_options=True
    )
    if 'linkSearch' not in st.session_state and 'Search Ticker On Cex' not in st.session_state and 'kolSearch' not in st.session_state and 'SingleSearch' not in st.session_state:
        
        if 'displayed' in st.session_state and next_timeframe !=None and  st.session_state['Timeframe'] != next_timeframe:
            st.session_state['Timeframe'] = next_timeframe
            if isinstance(next_timeframe,str):
                try:
                    hour_minute = next_timeframe.split(':')
                    hours_into_minutes = int(hour_minute[0]) 
                    minute = int(hour_minute[1])
                    next_timeframe = ( hours_into_minutes * 60) + minute
                except:
                    try:
                        next_timeframe = int(next_timeframe)
                    except:
                        st.error('Please Select Valid Timeframe')
                        st.stop()

            tweeted_token_details = st.session_state['tweeted_token_details']
            analyzor = token_tweeted_analyzor(tweeted_token_details,int(next_timeframe))
            df_data = add_to_csv(analyzor) 
            st.session_state['df_data'] = df_data
    elif ('linkSearch' in st.session_state or 'kolSearch' in st.session_state or 'SingleSearch' in st.session_state) and next_timeframe == None :
        add_to_csv(df_data)
    elif ('linkSearch' in st.session_state or 'kolSearch' in st.session_state or 'SingleSearch' in st.session_state) and next_timeframe != None:
        
        timeframe = st.session_state['Timeframe']+','+ str(next_timeframe)
        st.session_state['Timeframe'] = timeframe
        if 'linkSearch' in st.session_state:
            
            process = processor()
            with st.spinner('Fecthing Added Timeframe Prices'):
                if 'Search Ticker On Cex' in st.session_state:
                    combine_date_time =  datetime.combine(choose_date,choose_time)
                    tickers = contracts_input
                    start_date = str(combine_date_time)
                    data = process.SearchTickerOnCex(tickers,start_date,timeframe)
                else:
                    data = process.linkSearch(username_url,timeframe)
        elif 'kolSearch' in st.session_state :
            with st.spinner(f'Searching Early Tweets On {kolSearch} And Analyzing Account Involves. Please Wait ......'):
                TotalUsersToRetrieve = 5
                AnalyzeTweet =  10
                # pass
                if KolSearch_time:
                    search_time = set_time
                else:
                    search_time = None
                if kolSearch_From_date:
                    From_date= str(kolSearch_From_date)
                else:
                    From_date = None
                data = searchKeyword(
                    keyword=kolSearch,
                    date=str(kolSearch_date),
                    timeframe=timeframe,
                    from_date=From_date,
                    time=search_time,
                    limit= TotalUsersToRetrieve,
                    userTweetLimit=AnalyzeTweet,
                    followers_threshold=int(follower_threshold)
                    )
                if 'Error' in data:
                    st.error(data['Error'])
                    st.stop()
        else:
            # tweet_limit = 10
            with st.spinner(F'Procesing {username_url} Tweets With Added Timeframe'):
                data = SingleUserSearch(username_url,timeframe,tweet_limit)
            if 'Error' in data:
                st.error(data['Error'])
        df_data = add_to_csv(data) 
        st.session_state['df_data'] = df_data
    
   
       
    if 'linkSearch' not in st.session_state and 'kolSearch' not in st.session_state and 'SingleSearch' not in st.session_state:
        logging.info('Displaying Data')

        if 'For_Ai' in st.session_state:
            if 'prepare_for_AI' in st.session_state:
                prepare_for_AI = st.session_state['prepare_for_AI']
                Ai_response = GeminiRefine(Ai_assits_Data=prepare_for_AI)

                st.markdown(f":rainbow-background[{Ai_response}]")

        st.dataframe(df_data)

        st.session_state['displayed'] = 'yes'
        if 'Search_tweets_Contract' in st.session_state:
            st.session_state['Search_tweets_Contract_displayed'] = 'Search_tweets_Contract_displayed'
        st.session_state['download_dataframe'] = df_data

        # def convert_for_download(df_data):
        #     return df_data.to_csv().encode("utf-8")
        # csv = convert_for_download(df_data)
        col = st.columns([1,1])
        # with col[0]:
        #     st.download_button(
        #         label="Download CSV",
        #         data=csv,
        #         file_name="data.csv",
        #         key=1,
        #         mime="text/csv",
        #         icon=":material/download:"
        #     )
        with col[0]:
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

if 'df_data' in st.session_state: # For displaying the Tweeted data
    display(st.session_state['df_data'])



