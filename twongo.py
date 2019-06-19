###########################################################################################
## twongo.py - Al Tanner, Feb2019 - a twitter havester using MongoDB for data management ##
###########################################################################################

import os
import sys
import time
import glob
import tweepy
import pymongo
import logging
import datetime
import subprocess

import credentials
from mongo_ops import start_mongo, stop_mongo, index_mongo
from twongo_status import status_up, status_down
from twitter_ops import lookup_users, harvest


## set up a few run variables
start = time.time()
now = datetime.datetime.now()
client = pymongo.MongoClient('localhost', 27017)
db = client.twitter_db
collection = db.tweets
following_collection = db.following

## set up environment specific variables
if not os.path.exists('/.dockerenv'):   ## if not in docker container
    run_folder = os.getcwd() + '/'
    status_file = run_folder + 'STATUS'
    db_log_filename = '/'.join([run_folder, 'db_logs', now.strftime('%H:%M:%S_%d-%m-%Y') + '.log'])
    db_path = run_folder + '/db'
    csv_filename = run_folder + '/output/csv/' + now.strftime('%H:%M:%S_%d-%m-%Y') + ".csv"
    twongo_log_filename = '/'.join([run_folder, 'twongo_logs', now.strftime('%H:%M:%S_%d-%m-%Y') + '.log'])
    database_dump_path = run_folder + '/output'
else:                               ## if IS in docker container
    run_folder = '/root/host_interface/'
    status_file = '/root/host_interface/STATUS'
    db_log_filename = '/root/host_interface/db_logs/' + now.strftime('%H:%M:%S_%d-%m-%Y') + '.log'
    db_path = '/root/host_interface/db'
    twongo_log_filename = '/root/host_interface/twongo_logs/' + now.strftime('%H:%M:%S_%d-%m-%Y') + '.log'
    csv_filename = '/root/host_interface/output/csv/' + now.strftime('%H:%M:%S_%d-%m-%Y') + '.csv'
    database_dump_path = '/root/host_interface/output'

## check if MongoDB is present and correct
try:
    mongod_executable_path = subprocess.check_output(["which", "mongod"]).decode('utf-8').strip()
except:
    print(f"You don't seem to have MongoDB installed. Stopping.")
    sys.exit()
try:
    mongoexport_executable_path = subprocess.check_output(["which", "mongoexport"]).decode('utf-8').strip()
except:
    print(f"Mongoexport seems missing... stopping.")
    sys.exit()
try:
    mongodump_executable_path = subprocess.check_output(["which", "mongodump"]).decode('utf-8').strip()
except:
    print(f"Mongodump seems missing... stopping.")
    sys.exit()

## Check user list exists and get it
if not os.path.exists(run_folder + "user_list"):
    print(f'USAGE: please provide a list of users to follow, named "user_list".')
    sys.exit()
number_of_users_provided = sum(1 for line_exists in open(run_folder + "user_list") if line_exists)
screen_names = list(dict.fromkeys(line.strip() for line in open(run_folder + "user_list"))) # remove duplicates
screen_names = [name for name in screen_names if name] # remove empty lines

## Check or make directory structure
if not os.path.exists(run_folder + "/db"):
    print(f"MongoDB database folder seems absent, creating folder...")
    os.makedirs(run_folder + "/db")
if not os.path.exists(run_folder + "/db_logs"):
    print(f"DB log folder seems absent, creating folder...")
    os.makedirs(run_folder + "/db_logs")
if not os.path.exists(run_folder + "/twongo_logs"):
    print(f"Twongo log folder seems absent, creating folder...")
    os.makedirs(run_folder + "/twongo_logs")

## Set up logging
if "--log" in sys.argv: # if --log given as argument, create a logfile for this run
    logging.basicConfig(
        filename = twongo_log_filename,
        level=logging.INFO,
        format='',
        datefmt='%m/%d/%Y %I:%M:%S',)
    logger = logging.getLogger()
    print = logger.info
#    sys.stdout = open(twongo_log_filename, "a")
#    log = open(run_folder + '/twongo_logs/' + now.strftime('%Y-%m-%d_%H:%M:%S') + '.log', "a")
 #   sys.stdout = log # all print debugs to logfile
  #  sys.stderr = log # all stderr to logfile

## connect to Twitter API
auth = tweepy.OAuthHandler(credentials.CONSUMER_KEY, credentials.CONSUMER_SECRET)
auth.set_access_token(credentials.ACCESS_TOKEN, credentials.ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, retry_count=5, retry_delay=5, timeout=15)
try:
    api.verify_credentials()
except tweepy.error.TweepError:
    print(f"The API credentials do not seem valid: connection to Twitter refused.")
    sys.exit()

def export():

    """Export some fields from the tweets in MongoDB into a CSV file
    , backup and compress the database"""

    print(f"\nCreating CSV output file...")
    subprocess.call([mongoexport_executable_path, "--host=127.0.0.1", "--db", "twitter_db", "--collection", "tweets", "--type=csv", "--out", csv_filename, "--fields", "user.id_str,id_str,created_at,full_text"])
    print(f"\nBacking up the database...")
    subprocess.call([mongodump_executable_path, "-o", database_dump_path, "--host=127.0.0.1"])
    subprocess.call(["chmod", "-R", "0755", database_dump_path]) # hand back access permissions to host
    subprocess.call(['zip', '-jumq', run_folder + 'db_logs/db_logs.zip', run_folder] + glob.glob('db_logs/*.log'))
    subprocess.call(['zip', '-jumq', run_folder + 'twongo_logs/twongo_logs.zip', run_folder] + glob.glob('twongo_logs/*.log'))
    subprocess.call(['zip', '-jumq', run_folder + 'output/csv/csv.zip', run_folder] + glob.glob('output/csv/*.csv'))

############
## run it ##
############

if __name__ == "__main__":

    try:
        ## check/start mongodb
        start_mongo(mongod_executable_path, db_path, db_log_filename)
        ## modify status file
        status_up(collection, status_file)
        ## tidy up the database for better efficiency
        index_mongo(run_folder, db)
        ## get persistent user ids from screen names
        lookup_users(run_folder, screen_names, api)
        ## get tweets for each user and archive in mongodb
        harvest(run_folder, db, api, collection)
        ## create CSV ouput and backup mongodb
        export()
        ## modify status file
        status_down(collection, status_file, run_folder)
        ## shut down mongodb
        stop_mongo(client)

        print(f"\nAll done, twongo finished at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}, taking around {int(round((time.time() - start) / 60))} minutes.")

    except KeyboardInterrupt:
        print(f"\n\nCtrl-c, ok got it, just a second while I try to exit gracefully...")
        with open(status_file, "w+") as status:
            status.write(f"Twongo is currently idle, but was interruped by user on last run.\nThe most recent harvest was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\n")
        stop_mongo(client)
        sys.exit()

