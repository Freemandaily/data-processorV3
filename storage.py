import os
import sys,logging
import time
import pandas as pd
import streamlit as st
import gspread
from gspread_dataframe import set_with_dataframe

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s'
)

def add_to_csv(tweeted_token:dict)->None:
    logging.info('Foramating Data for Display')
    if 'kolSearch' in st.session_state:
        kolSearch(tweeted_token)
    if 'linkSearch' not in st.session_state and 'KolSearch' not in st.session_state:
        formated_data = []
        tweeted_token = { date:value for date,value in tweeted_token.items() if value}
        if tweeted_token:
            if 'Influencer_data' not in st.session_state:
                st.session_state['Influencer_data'] = { }
                st.toast('Adding Tweeted Token Data To Cvs File!')
        else:
            logging.error('Tokens  Contains Invalid Price')
            Error_message = {'Error':'Tokens  Contains Invalid Price','Message':'Adding Tweeted Token Data To Cvs File!'}
            return Error_message

        
        for username_Id,info in tweeted_token.items():
            try:
                for token_address,token_data in info.items():
                    data = collect_data(username_Id,token_data,token_address)
                    formated_data.append(data)
            except:
                pass
            
        for influencer_data in formated_data:
            score = 0
            for data_key,data_value in influencer_data.items():
                if data_key.split('_')[-1] == 'Score':
                    score += int(data_value)
            influencer_data['Total_Score'] = score
        
        max_column = 0
        for influencer_call_data in formated_data:
            if len(influencer_call_data) > max_column:
                max_column = len(influencer_call_data) 
            
        formated_data = [influencer_call_data for influencer_call_data in formated_data if len(influencer_call_data) == max_column ]

        new_entry = pd.DataFrame(formated_data)
        return new_entry
    elif 'linkSearch' in st.session_state :
        linkSearchDisplay(tweeted_token)
    # else:
    #     logging.info('About To display kolSearch')
    #     kolSearch(tweeted_token)

def collect_data(username_Id,token_data,token_address):
    if username_Id not in st.session_state['Influencer_data']:
        st.session_state['Influencer_data'][username_Id] = { }
    try:
        del st.session_state['Influencer_data'][username_Id]['Address']
        del st.session_state['Influencer_data'][username_Id]['Tweet_Url'] 
        del st.session_state['Influencer_data'][username_Id]['Total_Score']  
    except:
        pass
    for token_key,value in token_data.items():
        st.session_state['Influencer_data'][username_Id][token_key] = value
    
    st.session_state['Influencer_data'][username_Id]['Address'] = token_address

    try:
        st.session_state['Influencer_data'][username_Id]['Tweet_Url'] = f"https://x.com/{token_data['username']}/status/{token_data['Tweet_id']}"
        del st.session_state['Influencer_data'][username_Id]['Tweet_id']
    except Exception as e:
        pass
    
    data = st.session_state['Influencer_data'][username_Id]
    return data

def linkSearchDisplay(data):
    dataframes = {}
    symbols = []
    if data == None:
        logging.error('This Ticker Is Not Available On Binance And Bybit Yet')
        st.error('This Ticker Is Not Available On Binance And Bybit Yet')
        st.stop()

    validate = [ symbol for price_items in data for symbol,timeframe_data in price_items.items() if isinstance(timeframe_data,list)]
    if not validate:
        logging.error('This Ticker Is Not Available On Binance And Bybit Yet')
        st.error('This Ticker Is Not Available On Binance And Bybit Yet')
        st.stop()
    date_tweeted = data[-1]['date_tweeted']
    for item in data:
        symbol_dfs = {}
        for Token_symbol, value in item.items():
            if Token_symbol.startswith('$') and value != 'Not On Bybit':
                symbol_dfs[Token_symbol] = {
                    'Info': ['Entry_Price', 'Price', '%_Change', 'Peak_Price', '%_Entry_to_Peak', 'lowest_Price','Max_Drawdown']
                }
                for timeframe_entry in value:
                    symbol_dfs[Token_symbol][timeframe_entry['timeframe']] = [
                                                                            timeframe_entry['Entry_Price'],
                                                                            timeframe_entry['Price'],
                                                                            timeframe_entry['%_Change'],
                                                                            timeframe_entry['Peak_Price'],
                                                                            timeframe_entry['%_Entry_to_Peak'],
                                                                            timeframe_entry['lowest_Price'],
                                                                            timeframe_entry['Max_Drawdown']  
                    ]
                # Create DataFrame
                df = pd.DataFrame(symbol_dfs[Token_symbol])
                dataframes[Token_symbol] = df
                symbols.append(Token_symbol)
    if 'slide_index' not in st.session_state:
        st.session_state['slide_index'] = 0
        
    def next_slide():
        if st.session_state.slide_index < len(symbols) - 1:
            st.session_state['slide_index'] +=1

    def prev_slide():
        if st.session_state.slide_index > 0:
            st.session_state['slide_index'] -=1

    st.badge(f"Symbol : {symbols[st.session_state['slide_index']]}",color='orange')
    st.badge(f'Date Time: {date_tweeted}')
    st.dataframe(dataframes[symbols[st.session_state['slide_index']]])
    logging.info('Displayed Data')

    col1,col2 = st.columns([1,2])
    with col1:
        if st.button('Prev. Token',disabled=st.session_state['slide_index'] == 0):
            prev_slide()
    with col2:
        if st.button('Next Token',disabled=st.session_state['slide_index'] == len(symbols) -1 ) :
            next_slide()
    
    col = st.columns([1,1])
    with col[0]:
        df_data = dataframes[symbols[st.session_state['slide_index']]]
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

def kolSearch(data):
    rows = []
    print(data)
    for username, stats in data.items():
        row = {
            'Username': username,
            'TickerCalled': stats.get('TickerCalled', 0),
            'TotalScore': stats.get('TotalScore', 0),
            'AverageScore': stats.get('averageScore', float('nan'))  # Use NaN for missing averageScore
        }
        rows.append(row)

    # Create DataFrame
    df = pd.DataFrame(rows, columns=['Username', 'TickerCalled', 'TotalScore', 'AverageScore'])
    st.dataframe(df)