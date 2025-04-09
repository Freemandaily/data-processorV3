import os
import sys
import time
import pandas as pd

def add_to_csv(Influencer_name:str,tweeted_token:dict)->None:
    tweeted_token = { date:value for date,value in tweeted_token.items() if value}
    if tweeted_token:
        print('Adding Tweeted Token Data To Cvs File!')
        time.sleep(3)
    else:
        print('Tokens  Contains Invalid Price')
        sys.exit()

    formated_data = []
    for date,info in tweeted_token.items():
        for token_address,token_data in info.items():
            Influencer_data = {
                    "Influencer": f'@{Influencer_name}',
                    "Token": token_data['symbol'],
                    "Address": f'{token_address[:3]}...{token_address[-3:]}',
                    "Tweet Date": date[:10] ,
                    "Tweeted Price": f'   {token_data['Price_Tweeted_At']}     ',
                    "Price @5m     ": "     0      " if token_data['price_5m'] == None else f'  {token_data['price_5m']}    ' ,
                    "Price @10m     ":"     0      " if token_data['price_10m'] == None else f'  {token_data['price_10m']}    ',
                    "Price @15m     ":"     0      " if token_data['price_15m'] == None else f'    {token_data['price_15m']}   ',
                    "5m%change      " :"   0   " if token_data['price_10m%Increase'] == None else f'    {token_data['price_10m%Increase']}   ',
                    "10m%change     ":"    0  " if token_data['price_10m%Increase'] == None else f'    {token_data['price_10m%Increase']}   ',
                    "15m%change     ":"     0" if token_data['price_10m%Increase'] == None else f'    {token_data['price_10m%Increase']}   ',
                    "Token Contract": token_address
                    }
            formated_data.append(Influencer_data)
            
    new_entry = pd.DataFrame(formated_data)
    file_name = 'data.csv'
    if os.path.exists(file_name):
        existing_entry = pd.read_csv(file_name,sep='|')

        for index, row in new_entry.iterrows():
            check_duplicate = existing_entry[
            (existing_entry['Influencer'] == row['Influencer']) &
                (existing_entry['Tweet Date'] == row['Tweet Date']) &
                (existing_entry['Token'] == row['Token'])
            ].shape[0] > 0

            
            if check_duplicate:# Removing the duplicate Data from the influencer that are already in the csv file
                print("Found Already Existing Data...")
                new_entry.drop(index,inplace=True)
                time.sleep(2)


        if not new_entry.empty:
            combined_df = pd.concat([existing_entry, new_entry])
            combined_df.to_csv(file_name,sep='|',index=False)
            print("New Influencer Data Added To CSV file")
        else:
            print('All Found Datas Allready Exists In The File.\nChange TimeFrame And Try Again')
    else:
        new_entry.to_csv(file_name,sep='|',index=False)
        time.sleep(2)
        print("New Influencer Data Added To CSV file")


