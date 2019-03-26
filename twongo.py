###########################################################################################
## twongo.py - Al Tanner, Feb2019 - a twitter havester using MongoDB for data management ##
###########################################################################################

import os
import sys
import time
import glob
import json
import psutil
import tweepy
import pymongo
import logging
import datetime
import subprocess

## set up run variables
start = time.time()
times_limited = 0
private_accounts = 0
empty_accounts = 0
not_found = []
docker_env = 0
refresh_user_list = 0
get_friends_list = 0
now = datetime.datetime.now()
credentials = ""
client = pymongo.MongoClient('localhost', 27017)
db = client.twitter_db
collection = db.tweets
following_collection = db.following
mongod_executable_path = subprocess.check_output(["which", "mongod"]).decode('utf-8').strip()
mongoexport_executable_path = subprocess.check_output(["which", "mongoexport"]).decode('utf-8').strip()
mongodump_executable_path = subprocess.check_output(["which", "mongodump"]).decode('utf-8').strip()

## set up environment specific variables:
if "--refresh" in sys.argv:
    refresh_user_list = 1
if "--getfriends" in sys.argv:
    get_friends_list = 1
if os.path.exists("/.dockerenv"): ## is the process running in docker container, or locally?
    docker_env = 1                ## I'm in a docker
if docker_env == 0: # if NOT in docker container
    run_folder = (subprocess.check_output(["pwd"]).decode('utf-8').strip() + "/")
    log_filename = run_folder + "/db_logs/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".log"
    db_path = run_folder + "/db"
    credentials = run_folder + "/credentials"
    csv_filename = run_folder + "/output/csv/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".csv"
    database_dump_path = run_folder + "/output"
else:               # if IS in docker container
    run_folder = "/root/host_interface/"
    log_filename = "/root/host_interface/db_logs/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".log"
    db_path = "/root/host_interface/db"
    credentials = "/root/host_interface/credentials"
    csv_filename = "/root/host_interface/output/csv/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".csv"
    database_dump_path = "/root/host_interface/output"

## Check user list exists and get it
if not os.path.exists(run_folder + "user_list"):
    print('USAGE: please provide a list of users to follow, named "user_list".')
    exit(1)
screen_names = list(dict.fromkeys(line.strip() for line in open(run_folder + "user_list")))

## Check credentials file exists
if not os.path.exists(credentials):
    print("The credentials file doesn't seem to be here. Exiting.")
    print("If you are running this manually, please be in your run folder.")
    exit(1)

## Check or make directory structure
if not os.path.exists(run_folder + "/db"):
    print("MongoDB database folder seems absent, creating folder...")
    os.makedirs(run_folder + "/db")
if not os.path.exists(run_folder + "/db_logs"):
    print("DB log folder seems absent, creating folder...")
    os.makedirs(run_folder + "/db_logs")
if not os.path.exists(run_folder + "/twongo_logs"):
    print("Twongo log folder seems absent, creating folder...")
    os.makedirs(run_folder + "/twongo_logs")
if "--log" in sys.argv: # if --log given as argument, create a logfile for this run
    log = open(run_folder + '/twongo_logs/' + now.strftime('%Y-%m-%d_%H:%M:%S') + '.log', "a")
    sys.stdout = log # all print debugs to logfile

## Get Twitter API details from credentials file
cred_fields = {}
with open(credentials) as credentials:
    first4lines=credentials.readlines()[0:4]
    for line in first4lines: # put credentials into a dict
        line = line.strip()
        if " " not in line:
            print("The credentials file doesn't appear correct, please check and retry.")
            exit(1)
        (key, val) = line.split(' ')
        cred_fields[(key)] = val

## connect to Twitter API
auth = tweepy.OAuthHandler(cred_fields[("CONSUMER_KEY")], cred_fields[("CONSUMER_SECRET")])
auth.set_access_token(cred_fields[("ACCESS_TOKEN")], cred_fields[("ACCESS_TOKEN_SECRET")])
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
try:
    api.verify_credentials()
except tweepy.error.TweepError:
    print("The API credentials do not seem valid: connection to Twitter refused.")
    exit(1)


#####################
## build functions ##
#####################

 
def start_mongo_daemon():
    """look through running processes for the mongod deamon.
       ... if it isn't there, start the daemon."""
    now = datetime.datetime.now()
    if not "mongod" in (p.name() for p in psutil.process_iter()):
        print("\nIt doesn't look like the MongoDB daemon is running: starting daemon...")
        try:
            subprocess.Popen([mongod_executable_path, '--dbpath', db_path, '--logpath', log_filename])
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            print("There is a problem opening the MonogoDB daemon... halting.\n", e.output)
            exit(1)


def stop_mongo_daemon():
    client.close()
    print("\nAsking MongoDB to close...")
    subprocess.call(["pkill", "-15", "mongod"])
    while True:  
        try:
            subprocess.check_output(["pgrep", "mongod"])
        except subprocess.CalledProcessError:
            print("\nOK, MongoDB daemon closed.")
            break
        print('.', end='', flush=True)        
        time.sleep(1)    
        

def index_mongodb(): # tidy up the database
    if not os.path.isfile(run_folder + "/db/WiredTiger"):
        return
    print("\nIndexing MongoDB...")
    db.tweets.create_index([("id_str", pymongo.ASCENDING)], unique=True, dropDups=True)


def lookup_users():
    if refresh_user_list == 0 and os.path.exists(run_folder + "user_list.ids"):
        return
    with open(run_folder + "user_list") as file:
        duplicate_users = []
        lines = [x.strip() for x in file.readlines()]
        for line in lines:
            if lines.count(line) > 1:
                duplicate_users.append(line)
        if len(duplicate_users) > 0:
            print("\nThere are duplicates users in your list:", set(duplicate_users))
    print("Converting user screen names to persistent id numbers...")
    # this function should be fine with both unix and dos formatted files
    # Count the number of screen names in the input file
    non_blank_count = 0
    with open(run_folder + "user_list") as count_file:
        for line in count_file:
            if line.strip():
                non_blank_count += 1

    # chunks splits the screen_name list into manageable blocks:
    def chunks(l, n):
        for i in range(0, len(l), n):     # For item i in a range that is a length of l,
            yield l[i:i+n]                # Create an index range for l of n items:
    
    # Query twitter with the comma separated list
    id_list = []        # empty list for id to go into
    for chunk in list(chunks(screen_names, 42)): # split list into manageable chunks of 42
        comma_separated_string = ",".join(chunk) # lookup takes a comma-separated list
        for user in chunk:
            try:
                user = api.get_user(screen_name = user)
                id_list.append(user.id) # get the id and put it in the id_list   
                print('.', end='', flush=True)
            except tweepy.error.TweepError as e:
                not_found.append(user) # if not found, put user in not found list

    # Write user codes to file.
    with open(run_folder + "user_list.ids", 'w') as id_file:
        for id in id_list:
            id_file.write("%s\n" % id)                            # write to id file
        print("\nOK,", len(id_list), "of", len(screen_names), "ID numbers written to --> user_list.ids") 
    if len(not_found) > 0: # if users are not found, put into missing user file
        print("Warning:", len(not_found), "screen names did not return ID codes.")
        with open(run_folder + "user_list.notfound", 'w') as missing_user_file:
            for missing_user in not_found:
                missing_user_file.write("%s\n" % missing_user)    # write to missing user file  
        print("Missing users written to --> user_list.notfound")


def get_tweets(twitter_id, times_limited, private_accounts, empty_accounts):
    ## check if this user history has been acquired
    if db.tweets.count_documents({"user.id": twitter_id}) > 0:
        ## we already have this user's timeline, just get recent tweets
        try:
            print("User", twitter_id, "is in the database, shallow acquisition cycle...")
            alltweets = []
            new_tweets = api.user_timeline(id=twitter_id, count=200,
                                           tweet_mode='extended', exclude_replies=True)
            alltweets.extend(new_tweets)
        except tweepy.TweepError as tweeperror:
            print("Not possible to acquire timeline of", twitter_id, ":", tweeperror)
            private_accounts += 1
    else:
        ## this user isn't in database: get <3200 tweets if possible
        try:
            print("User", twitter_id, "is new, deep acquisition cycle...")
            alltweets = [] # IS BELOW REDUNDANT?
            new_tweets = api.user_timeline(id=twitter_id, count=200,
                                           tweet_mode='extended', exclude_replies=True)
            alltweets.extend(new_tweets)
            try:
                oldest = alltweets[-1].id - 1
                while len(new_tweets) > 0:
                    new_tweets = api.user_timeline(id=twitter_id, count=200, max_id=oldest,
                                                   tweet_mode='extended', exclude_replies=True)
                    alltweets.extend(new_tweets)
                    oldest = alltweets[-1].id - 1
            except IndexError:
                print("Empty timeline for user", twitter_id, ": skipping.")
                empty_accounts += 1
        except tweepy.TweepError as tweeperror:
            print("Not possible to acquire timeline of", twitter_id, ":", tweeperror)
            private_accounts += 1
        except tweepy.RateLimitError as rateerror:
            print("Rate limit reached, waiting for cooldown...")
            times_limited += 1

    ## update the database with the acquired tweets for this user 
#    duplicates = 0
 #   uniques = 0
    for tweet in alltweets:
        try:
            try:
                collection.update_one(tweet._json, {'$set': tweet._json}, upsert=True)
  #              uniques += 1
            except pymongo.errors.DuplicateKeyError:
                pass
        except IndexError:
            print("User", user, "has no tweets to insert.")
   #         duplicates += 1
   # print(duplicates, " of these were duplicates and not inserted")
   # print(uniques, " were new and inserted")


def get_friends(twitter_id): ## get the "following" list for this user
    friend_list = []
    try:
        for friend in tweepy.Cursor(api.friends_ids, id = twitter_id, count = 200).pages():
            friend_list.extend(friend) # put the friends into a list
    except tweepy.RateLimitError as rateerror:
        print("Rate limit reached, waiting for cooldown...", rateerror)
        times_limited += 1
    try:
        for person in friend_list:     # insert those into a mongodb collection called "following"
            following_collection.update_one({"user_id": twitter_id}, {"$addToSet": {"following": [person]}}, upsert=True)
    except: # make this more specific?
        print("Problem putting friends into MongoDB...")
        #    print(*friend_list, sep='\n')


def export(): # export and backup the database
    print("\nCreating CSV output file...")
    subprocess.call([mongoexport_executable_path, "--host=127.0.0.1", "--db", "twitter_db", "--collection", "tweets", "--type=csv", "--out", csv_filename, "--fields", "user.id_str,id_str,created_at,full_text"])
    print("\nBacking up the database...")
    subprocess.call([mongodump_executable_path, "-o", database_dump_path, "--host=127.0.0.1"])
    subprocess.call(["chmod", "-R", "0755", database_dump_path]) # hand back access permissions to host
    subprocess.call(['zip', '-jumq', run_folder + 'db_logs/db_logs.zip', run_folder] + glob.glob('db_logs/*.log'))
    subprocess.call(['zip', '-jumq', run_folder + 'twongo_logs/twongo_logs.zip', run_folder] + glob.glob('twongo_logs/*.log'))
#    subprocess.call(['zip', '-jumq', run_folder + 'output/csv/csv.zip', run_folder] + glob.glob('output/csv/*.csv'))


def report(): # do some post-process checks and report.
    fail_accounts = private_accounts + empty_accounts + len(not_found)
    print("\nOK, tweet timelines acquired from", (len(screen_names) - fail_accounts), "of", len(screen_names), "accounts.")
    print(private_accounts, "accounts were private.")
    print(empty_accounts, "accounts were empty.")
#    if duplicate_users:
 #        print(len(set(duplicate_users)), "were duplicate users:", set(duplicate_users))
    print(len(not_found), "accounts do not seem to exist, see user_list.not_found")
    print("Twitter rate limited this process", times_limited, "times.")

def harvest():
    index_counter = 0
    ## generate user id list from user2id output file
    users_to_follow = [int(line.rstrip('\n')) for line in open(run_folder + "user_list.ids")]
    now = datetime.datetime.now()
    print("\nStarting tweet harvest at", now.strftime('%d-%m-%Y_%H:%M:%S'), "...")
    try: ## iterate through this list of ids.
        for user in users_to_follow:
            if index_counter % 100 == 0: # every 100 users index the database
                index_mongodb()
            #get_tweets(user)
            get_tweets(user, times_limited, private_accounts, empty_accounts)   ## get all their tweets and put into mongodb
            if get_friends_list == 1:
                get_friends(user) ## this tends to rate limit, but tweet harvest doesn't (?!)
            index_counter += 1
    except Exception as e:
        print(e)


############
## run it ##
############
if __name__ == "__main__":

    start_mongo_daemon()   ## check/start mongodb

    index_mongodb()        ## tidy db up for faster access

    lookup_users()         ## get persistent user ids from screen names

    harvest()              ## get tweets for each user and archive in mongodb

    export()               ## create CSV ouput and backup mongodb

    report()               ## return some debug statistics

    stop_mongo_daemon()    ## shut down mongodb

    now = datetime.datetime.now()
    end = time.time()
    process_time = int(round((end - start) / 60))
    print("\nAll done, twongo finished at", now.strftime('%d-%m-%Y_%H:%M:%S') + ", taking around", process_time, "minutes.")
