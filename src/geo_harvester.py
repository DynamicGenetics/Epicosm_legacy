# -*- coding: utf-8 -*-

import tweepy
import json
import sys
import signal
import os
import time
from pymongo import MongoClient
import pymongo
from urllib3.exceptions import ProtocolError

# local imports
from modules import mongo_ops, geo_boxes, env_config, csv2liwc, df_cleaning_functions, twitter_ops


def signal_handler(signal, frame):

    """Handle interrupts from ctrl-c, and other interrupt signals"""

    if signal == 2:
        print(f"\n\nCtrl-c, ok got it, just a second while I try to exit gracefully...")
    mongo_ops.stop_mongo(env.db_path)
    sys.exit(0)


class StreamListener(tweepy.StreamListener):

    """tweepy.StreamListener is a class provided by tweepy used to access
    the Twitter Streaming API to collect tweets in real-time.
    """

    def on_connect(self):

        """Report the connection was successful"""

        print("Connected to the Twitter streaming server.")


    def on_error(self, status_code):

        """Catch some common errors."""

        if status_code == 401:
            print(f"\n!!! Authorisation failed. Have you put your API keys into /modules/credentials.py?")
            mongo_ops.stop_mongo()
            sys.exit(0)
        while status_code == 420:
            print(f"\n!!! Twitter API rate limit reached; trying again in 20 seconds.")
            time.sleep(21)
            stream.filter(locations=geo_boxes.boxes)
        while status_code == 500:
            print(f"\n!!! Twitter seems very busy; trying again in 5 seconds.")
            time.sleep(6)
            stream.filter(locations=geo_boxes.boxes)


    def on_data(self, data):

        """Put incoming tweets into DB, put out a csv and analyse sentiment"""

        # Deal with the incoming json
        datajson = json.loads(data)

        # LIWC doesn't like tweets which are just numbers (bots tweet this sometimes?)
        # so, here we skip tweets with no letters in
        if not any(tweettext.isalpha() for tweettext in datajson.get('text')):
            print("This tweet didn't contain letters - skipping.")
            return

        # True or False look like booleans to liwc
        if datajson.get('text') in ("True", "False"):
            print("Boolean misinterpretation... ignoring")
            return

        # put raw tweet into 'geotweets_collection' of the 'geotweets' database.
        db.geotweets_collection.insert_one(datajson)

        # export the most recent tweet as csv so it can be sentiment analysed
        mongo_ops.export_latest_tweet(mongoexport_executable_path, env.epicosm_log_filename)

        # turn most recent tweet into sentiment metrics
        # !! --- here we need latest_tweet > vader
        # !! csv > df
        # !! df appending with vader scores
        # !! df > geojson
        csv2liwc.liwc_analysis(env.latest_geotweet, category_names, parse)

        # bring sentiment analysis back into 'geotweets_analysed' of 'geotweets' database
        mongo_ops.import_analysed_tweet(mongoimport_executable_path, 'latest_geotweet.csvLIWC', env.epicosm_log_filename)


if __name__ == "__main__":

    ## Set up interrupt signal handling
    signal.signal(signal.SIGINT, signal_handler)

    ## Set up environment paths
    env = env_config.EnvironmentConfig()

    # verify credentials
    credentials, auth, api = twitter_ops.get_credentials()

    ## assign dictionary
    if len(sys.argv) != 2:
        print(f'Please assign your dictionary for sentiment analysis.')
        print(f'eg: python geo_harvester.py LIWC.dic')
        exit(0)
    dictionary = sys.argv[1]
    parse, category_names = csv2liwc.load_dictionary(dictionary)

    ## See if the Mongo environment looks right
    mongod_executable_path, mongoexport_executable_path, mongodump_executable_path, mongoimport_executable_path = mongo_ops.mongo_checks()

    ## Check or make directory structure
    if not os.path.exists(env.run_folder + '/db'):
        print(f"MongoDB database folder seems absent, creating folder...")
        os.makedirs(env.run_folder + '/db')
    if not os.path.exists(env.run_folder + '/db_logs'):
        print(f"DB log folder seems absent, creating folder...")
        os.makedirs(env.run_folder + '/db_logs')

    ## Spin up a MongoDB server
    mongo_ops.start_mongo(mongod_executable_path,
                          env.db_path,
                          env.db_log_filename,
                          env.epicosm_log_filename)

    ## Start instance of stream listener
    stream_listener = StreamListener(api=tweepy.API(wait_on_rate_limit=True))
    stream = tweepy.Stream(auth=auth, listener=stream_listener)
    client = MongoClient()
    db = client.geotweets
    while True:
        try: # catch connection exceptions. needs logging.
            stream.filter(locations=geo_boxes.boxes)
        except (ProtocolError, AttributeError) as e:
            print("Protocol/Attribute error, ignoring:", e)
        except (pymongo.errors.ServerSelectionTimeoutError, pymongo.errors.AutoReconnect) as e:
            print("Is MongoDB down? trying to restart it...", e)
            mongo_ops.stop_mongo(env.db_path) # refresh
            mongo_ops.start_mongo(mongod_executable_path,
                          env.db_path,
                          env.db_log_filename)
        except TypeError as e:
            print("There was a TypeError, very strange...", e)
        except tweepy.error.TweepError as e:
            print("Tweepy:", e) # catches rate limits and timeouts
        except Exception as e:
            print("Something went wrong there:", e)
