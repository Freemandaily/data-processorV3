import sys
from TweetData import processor
from priceFeed import token_tweeted_analyzor


username = input('Enter Influener X Handle\n')
time_frame = input('Choose TimeFrame eg 7,30,90')
processor = processor(username,timeframe=7)
tweeted_token_details = processor.processTweets()
add = token_tweeted_analyzor(tweeted_token_details,influencer_username=username)
