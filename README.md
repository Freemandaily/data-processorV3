# Data-Extraction-and-Processing
This is an analyst Module Whch serves the purpose of extracting  and Processing Token tweeted by you favourite X handle To understand the impact of handle toward  TOKEN..  

### Key Features
- **Fetching tweets from a handle within specified timeframe day( Default timeframe  is 7)**
- **Extracts Token Symbol and contract addresses mentioned in each tweets**
- **Using  the Tweeted Timestamp, retrieves the historical price data of the token after the  tweet**
- **Stores the data in a csv file**


### Requirements and Installations
- **Bearer Token from X Developer account**
- **Moralis API Key**
- **tweepy X library : ```pip install tweepy```**
- **pandas library: ```pip install pandas```**
- **pytz library : ```pip install pytz```**
**Add the Bearer Token and moralis Api key into the ```key.json``` file** 


### Usage
- **python3 main.py**
- **Enter Influencer Username  and timeFrame To Analyze, highest number of pages to retrieve is 300, adjust according**
  Note: The script uses jupiter project token list to matches the token symbol , you can try to match token symbols extensively by adding "No" to the "token_tweeted_analyzor" function call in "main.py"
  
