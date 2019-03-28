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
duplicate_users = []
docker_env = 0
refresh_user_list = 0
get_friends_list = 0
now = datetime.datetime.now()
credentials = ""
client = pymongo.MongoClient('localhost', 27017)
db = client.twitter_db
collection = db.tweets
following_collection = db.following

## check if MongoDB is present and correct
try:
    mongod_executable_path = subprocess.check_output(["which", "mongod"]).decode('utf-8').strip()
except:
    print(f"You don't seem to have MongoDB installed. Stopping.")
    sys.exit(1)
try:
    mongoexport_executable_path = subprocess.check_output(["which", "mongoexport"]).decode('utf-8').strip()
except:
    print(f"Mongoexport seems missing... stopping.")
    sys.exit(1)
try:
    mongodump_executable_path = subprocess.check_output(["which", "mongodump"]).decode('utf-8').strip()
except:
    print(f"Mongodump seems missing... stopping.")
    sys.exit(1)
    
## set up environment specific variables:
if "--refresh" in sys.argv:
    refresh_user_list = 1
if "--getfriends" in sys.argv:
    get_friends_list = 1
if os.path.exists("/.dockerenv"): ## is the process running in docker container, or locally?
    docker_env = 1                ## I'm in a docker
if docker_env == 0: # if NOT in docker container
    run_folder = (subprocess.check_output(["pwd"]).decode('utf-8').strip() + "/")
    status_file = run_folder + "STATUS"
    db_log_filename = run_folder + "/db_logs/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".log"
    db_path = run_folder + "/db"
    credentials = run_folder + "/credentials"
    csv_filename = run_folder + "/output/csv/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".csv"
    twongo_log_filename = run_folder + "/twongo_logs/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".log"
    database_dump_path = run_folder + "/output"
else:               # if IS in docker container
    run_folder = "/root/host_interface/"
    status_file = "/root/host_interface/STATUS"
    db_log_filename = "/root/host_interface/db_logs/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".log"
    db_path = "/root/host_interface/db"
    credentials = "/root/host_interface/credentials"
    twongo_log_filename = "/root/host_interface/twongo_logs/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".log"
    csv_filename = "/root/host_interface/output/csv/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".csv"
    database_dump_path = "/root/host_interface/output"

## Check user list exists and get it
if not os.path.exists(run_folder + "user_list"):
    print(f'USAGE: please provide a list of users to follow, named "user_list".')
    exit(1)
screen_names = list(dict.fromkeys(line.strip() for line in open(run_folder + "user_list")))

## Check credentials file exists
if not os.path.exists(credentials):
    print(f"The credentials file doesn't seem to be here. Exiting.")
    print(f"If you are running this manually, please be in your run folder.")
    exit(1)

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
logging.basicConfig(
    filename = twongo_log_filename,
    level=logging.INFO,
    format='',
    datefmt='%m/%d/%Y %I:%M:%S',)
logger = logging.getLogger()

if "--log" in sys.argv: # if --log given as argument, create a logfile for this run
    print = logger.info
#    sys.stdout = open(twongo_log_filename, "a")
#    log = open(run_folder + '/twongo_logs/' + now.strftime('%Y-%m-%d_%H:%M:%S') + '.log', "a")
 #   sys.stdout = log # all print debugs to logfile
  #  sys.stderr = log # all stderr to logfile

## Get Twitter API details from credentials file
cred_fields = {}
with open(credentials) as credentials:
    first4lines=credentials.readlines()[0:4]
    for line in first4lines: # put credentials into a dict
        line = line.strip()
        if " " not in line:
            print(f"The credentials file doesn't appear correct, please check and retry.")
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
    print(f"The API credentials do not seem valid: connection to Twitter refused.")
    exit(1)


#####################
## build functions ##
#####################

 
def start_mongo_daemon():
    """look through running processes for the mongod deamon.
       ... if it isn't there, start the daemon."""
    if not "mongod" in (p.name() for p in psutil.process_iter()):
        print(f"\nIt doesn't look like the MongoDB daemon is running: starting daemon...")
        try:
            subprocess.Popen([mongod_executable_path, '--dbpath', db_path, '--logpath', db_log_filename])
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            print(f"There is a problem opening the MonogoDB daemon... halting.\n", e.output)
            exit(1)


def stop_mongo_daemon():
    client.close()
    print(f"\nAsking MongoDB to close...")
    subprocess.call(["pkill", "-15", "mongod"])
    while True:  
        try:
            subprocess.check_output(["pgrep", "mongod"])
        except subprocess.CalledProcessError:
            print(f"\nOK, MongoDB daemon closed.")
            break
        if "--log" not in sys.argv:
            print(".", end='', flush=True)        
        time.sleep(1)    
        

def index_mongodb(): # tidy up the database
    if not os.path.isfile(run_folder + "/db/WiredTiger"):
        return
    print(f"\nIndexing MongoDB...")
    db.tweets.create_index([("id_str", pymongo.ASCENDING)], unique=True, dropDups=True)


def status_up():
    with open(status_file, "w+") as status:
        status.write("Twongo is currently running.\n")


def status_down():
    with open(status_file, "w+") as status:
        status.write(f"Twongo is currently idle.\nThe most recent harvest was {datetime.datetime.now().strftime('%d-%m-%Y_%H:%M:%S')}\n")


def lookup_users():
    global duplicate_users
    if refresh_user_list == 0 and os.path.exists(run_folder + "user_list.ids"):
        return
    with open(run_folder + "user_list") as file:
        lines = [x.strip() for x in file.readlines()]
        for line in lines:
            if lines.count(line) > 1:
                duplicate_users.append(line)
        if len(duplicate_users) > 0:
            print(f"\nWarning: there are {len(set(duplicate_users))} duplicate users in your list.")
        with open(run_folder + "user_list.duplicates", 'w') as duplicate_user_file:
            for duplicate_user in set(duplicate_users):
                duplicate_user_file.write("%s\n" % duplicate_user)
    print(f"Converting user screen names to persistent id numbers...")
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
                if "--log" not in sys.argv:
                    print('.', end='', flush=True)
            except tweepy.error.TweepError as e:
                not_found.append(user) # if not found, put user in not found list
        print(f"")

    # Write user codes to file.
    with open(run_folder + "user_list.ids", 'w') as id_file:
        for id in id_list:
            id_file.write("%s\n" % id)                            # write to id file
    if len(not_found) > 0: # if users are not found, put into missing user file
        print(f"\nWarning: {len(not_found)} users were not found as having an account.")
        with open(run_folder + "user_list.notfound", 'w') as missing_user_file:
            for missing_user in not_found:
                missing_user_file.write("%s\n" % missing_user)    # write to missing user file


def get_tweets(twitter_id):
    global times_limited
    global private_accounts
    global empty_accounts
    ## check if this user history has been acquired
    if db.tweets.count_documents({"user.id": twitter_id}) > 0:
        ## we already have this user's timeline, just get recent tweets
        try:
            print(f"User {twitter_id} is in the database, shallow acquisition cycle...")
            alltweets = []
            new_tweets = api.user_timeline(id=twitter_id, count=200,
                                           tweet_mode='extended', exclude_replies=True)
            alltweets.extend(new_tweets)
        except tweepy.TweepError as tweeperror:
            print(f"Not possible to acquire timeline of {twitter_id} : {tweeperror}")
            private_accounts += 1
    else:
        ## this user isn't in database: get <3200 tweets if possible
        try:
            print(f"User {twitter_id} is new, deep acquisition cycle...")
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
                print(f"Empty timeline for user {twitter_id} : skipping.")
                empty_accounts += 1
        except tweepy.TweepError as tweeperror:
            print(f"Not possible to acquire timeline of {twitter_id} : {tweeperror}")
            private_accounts += 1
        except tweepy.RateLimitError as rateerror:
            print(f"Rate limit reached, waiting for cooldown...")
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
            print(f"User {user} has no tweets to insert.")
   #         duplicates += 1
   # print(duplicates, " of these were duplicates and not inserted")
   # print(uniques, " were new and inserted")


def get_friends(twitter_id): ## get the "following" list for this user
    friend_list = []
    try:
        for friend in tweepy.Cursor(api.friends_ids, id = twitter_id, count = 200).pages():
            friend_list.extend(friend) # put the friends into a list
    except tweepy.RateLimitError as rateerror:
        print(f"Rate limit reached, waiting for cooldown... {rateerror}")
        times_limited += 1
    try:
        for person in friend_list:     # insert those into a mongodb collection called "following"
            following_collection.update_one({"user_id": twitter_id}, {"$addToSet": {"following": [person]}}, upsert=True)
    except: # make this more specific?
        print(f"Problem putting friends into MongoDB...")
        #    print(*friend_list, sep='\n')


def export(): # export and backup the database
    print(f"\nCreating CSV output file...")
    subprocess.call([mongoexport_executable_path, "--host=127.0.0.1", "--db", "twitter_db", "--collection", "tweets", "--type=csv", "--out", csv_filename, "--fields", "user.id_str,id_str,created_at,full_text"])
    print(f"\nBacking up the database...")
    subprocess.call([mongodump_executable_path, "-o", database_dump_path, "--host=127.0.0.1"])
    subprocess.call(["chmod", "-R", "0755", database_dump_path]) # hand back access permissions to host
    subprocess.call(['zip', '-jumq', run_folder + 'db_logs/db_logs.zip', run_folder] + glob.glob('db_logs/*.log'))
    subprocess.call(['zip', '-jumq', run_folder + 'twongo_logs/twongo_logs.zip', run_folder] + glob.glob('twongo_logs/*.log'))
#    subprocess.call(['zip', '-jumq', run_folder + 'output/csv/csv.zip', run_folder] + glob.glob('output/csv/*.csv'))


def report(): # do some post-process checks and report.
    fail_accounts = private_accounts + empty_accounts + len(not_found)
    total_users_provided = subprocess.check_output(["grep", "-cve", "'^\s*$'", run_folder + "user_list"]).decode('utf-8').strip()
    print(f"\nOK, tweet timelines acquired from {(len(screen_names) - fail_accounts)} of {total_users_provided} accounts.")
    if duplicate_users: print(f"{len(set(duplicate_users))} accounts were duplicates (see user_list.duplicates).")
    if not_found: print(f"{len(not_found)} accounts were not found (see user_list.notfound).")
    if private_accounts: print(f"{private_accounts} accounts were private.")
    if empty_accounts: print(f"{empty_accounts} accounts were empty.")
    print(f"Twitter rate limited this process {times_limited} times.")


def harvest():
    index_counter = 0
    ## generate user id list from user2id output file
    users_to_follow = [int(line.rstrip('\n')) for line in open(run_folder + "user_list.ids")]
    now = datetime.datetime.now()
    print(f"\nStarting tweet harvest at {now.strftime('%d-%m-%Y_%H:%M:%S')} ...")
    try: ## iterate through this list of ids.
        for twitter_id in users_to_follow:
            if index_counter % 100 == 0: # every 100 users index the database
                index_mongodb()
            get_tweets(twitter_id)  ## get all their tweets and put into mongodb
            if get_friends_list == 1:
                get_friends(twitter_id) ## this tends to rate limit, but tweet harvest doesn't (?!)
            index_counter += 1
    except Exception as e:
        print(f"{e}")


############
## run it ##
############
if __name__ == "__main__":

    status_up()            ## modify status file

    start_mongo_daemon()   ## check/start mongodb

    lookup_users()         ## get persistent user ids from screen names

    harvest()              ## get tweets for each user and archive in mongodb

    export()               ## create CSV ouput and backup mongodb

    report()               ## give some basic stats on the run

    stop_mongo_daemon()    ## shut down mongodb

    print(f"\nAll done, twongo finished at {datetime.datetime.now().strftime('%d-%m-%Y_%H:%M:%S')}, taking around {int(round((time.time() - start) / 60))} minutes.")

    status_down()          ## modify status file
          
