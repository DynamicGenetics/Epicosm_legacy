####################################
## twongo.py - Al Tanner, Feb2019 ##
## a twitter havester using       ##
## MongoDB for data management    ##
####################################

import json
import tweepy
import pymongo
import sys
import os
import subprocess
import psutil
import time
import datetime
import logging

## set up run variables
times_limited = 0
private_accounts = 0
empty_accounts = 0
the_date = datetime.datetime.now().date()
run_folder = subprocess.check_output(["pwd"]).decode('utf-8').strip()
client = pymongo.MongoClient('localhost', 27017)
db = client.twitter_db
collection = db.tweets
following_collection = db.following

## USAGE, if no user file provided
if not len(sys.argv) == 2:
    print("USAGE: please provide a list of users to follow.")
    print("EG: python twongo.py user_list")
    exit(1)

## Check that the userlist exists ####################### make this consistent with container!!!!!
#print(run_folder + "/" + sys.argv[1])
#if not os.path.exists(run_folder + "/" + sys.argv[1]):
if not os.path.exists(sys.argv[1]):
    print("The user list", sys.argv[1], "doesn't seem to be here. Exiting.")
    exit(1)

## Check the credentials file is present and looks correct
if not os.path.exists(run_folder + "/" + "credentials"):
    print("The credentials file doesn't seem to be here. Exiting.")
    exit(1)

## Check database folder exists, or create it
if not os.path.exists(run_folder + "/db"):
    print("MongoDB database folder seems absent, creating folder...")
    os.makedirs(run_folder + "/db")

## Check log folders exists, or create them
if not os.path.exists(run_folder + "/db_logs"):
    print("DB log folder seems absent, creating folder...")
    os.makedirs(run_folder + "/db_logs")
if not os.path.exists(run_folder + "/twongo_logs"):
    print("Twongo log folder seems absent, creating folder...")
    os.makedirs(run_folder + "/twongo_logs")
log = open(run_folder + '/twongo_logs/' + the_date.strftime('%d-%m-%Y') + '.log', "a")
sys.stdout = log # all print to logfile

## Get Twitter API details from credentials file
cred_fields = {}
with open(run_folder + "/" "credentials") as credentials:
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
    if "mongod" in (p.name() for p in psutil.process_iter()):
        print("\nMongoDB daemon is running... nice.\n")
    else:
        print("\nIt doesn't look like the MongoDB daemon is running: starting daemon...")
        try:
            log_filename = run_folder + "/db_logs/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".log"
            db_path = run_folder + "/db"
            mongod_path = subprocess.check_output(["which", "mongod"]).decode('utf-8').strip()
            subprocess.Popen([mongod_path, '--dbpath', db_path, '--logpath', log_filename])
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            print("There is a problem opening the MonogoDB daemon... halting.\n", e.output)
            exit(1)


def stop_mongo_daemon():
    client.close()
    subprocess.call(['pkill', '-2', 'mongod'])
    time.sleep(1) # Better way of doing this function?
    try: # look for mongod in processes
        subprocess.check_output(['pgrep', 'mongod'])
        print("\nClosing MongoDB didn't seem to work.")
    except:
        print("\nMongoDB now closed.")


def lookup_users():
    print("\nConverting users in", sys.argv[1], "to persistent id numbers...")

    # Count the number of screen names in the input file
    non_blank_count = 0
    with open(sys.argv[1]) as count_file:
        for line in count_file:
            if line.strip():
                non_blank_count += 1

    # Make a list from the input file of screen names
    screen_names = [line.strip() for line in open(sys.argv[1])] # clean up any whitespace
    screen_names = [_f for _f in screen_names if _f]            # clean up any empty lines

    # chunks splits the screen_name list into manageable blocks:
    def chunks(l, n):
        for i in range(0, len(l), n):     # For item i in a range that is a length of l,
            yield l[i:i+n]                # Create an index range for l of n items:
    
    # Query twitter with the comma separated list
    id_list = []        # empty list for id to go into
    not_found = []      # empty list for users not found
    for chunk in list(chunks(screen_names, 42)): # split list into manageable chunks of 42
        comma_separated_string = ",".join(chunk) # lookup takes a comma-separated list
        for user in chunk:
            try:
                user = api.get_user(screen_name = user)
                id_list.append(user.id) # get the id and put it in the id_list   
            except tweepy.error.TweepError as e:
                not_found.append(user) # if not found, put user in not found list

    # Write user codes to file.
    with open(sys.argv[1] + ".ids", 'w') as id_file:
        for id in id_list:
            id_file.write("%s\n" % id)                            # write to id file
        print("OK,", len(id_list), "of", non_blank_count, "ID numbers written to -->", sys.argv[1] + ".ids") 
    if len(not_found) > 0: # if users are not found, put into missing user file
        print("Warning:", len(not_found), "screen names did not return ID codes.")
        with open(sys.argv[1] + ".notfound", 'w') as missing_user_file:
            for missing_user in not_found:
                missing_user_file.write("%s\n" % missing_user)    # write to missing user file  
        print("Missing users written to -->", sys.argv[1] + ".notfound")


def get_tweets(twitter_id):
    # are these globals ok?
    global times_limited
    global private_accounts
    global empty_accounts
    ## check if this user history has been acquired
    if db.tweets.count_documents({"user.id": twitter_id}) > 0:
        try:
        ## we already have this user's timeline, just get recent tweets
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
    ## index mongodb for duplicate avoidance and speed
    db.tweets.create_index([("id_str", pymongo.ASCENDING)], unique=True, dropDups=True)    
    now = datetime.datetime.now()
    csv_filename = run_folder + "/output/csv/" + now.strftime('%Y-%m-%d_%H:%M:%S') + ".csv"
    print("\nCreating CSV output file...")
    mongoexport_path = subprocess.check_output(["which", "mongoexport"]).decode('utf-8').strip()
    subprocess.call([mongoexport_path, "--host=127.0.0.1", "--db", "twitter_db", "--collection", "tweets", "--type=csv", "--out", csv_filename, "--fields", "user.id_str,id_str,created_at,full_text"])
    print("\nBacking up the database...")
    database_path = run_folder + "/output"
    mongodump_path = subprocess.check_output(["which", "mongodump"]).decode('utf-8').strip()
    subprocess.call([mongodump_path, "-o", database_path, "--host=127.0.0.1"])


def report(): # do some post-process checks and report.
    users_to_follow = [int(line.rstrip('\n')) for line in open(sys.argv[1] + '.ids')]
    number_of_users_to_follow = len(users_to_follow)
    with open(sys.argv[1]) as f:
        non_blank_lines = sum(not line.isspace() for line in f)
    non_existent_accounts = non_blank_lines - number_of_users_to_follow
    fail_accounts = private_accounts + empty_accounts + non_existent_accounts
    success_accounts = non_blank_lines - fail_accounts
    print("\nOK, tweet timelines acquired from", success_accounts, "of", (success_accounts + fail_accounts), "accounts.")
    print(private_accounts, "accounts were private.")
    print(empty_accounts, "accounts were empty.")
    print(non_existent_accounts, "accounts do not seem to exist.")
    print("Twitter rate limited this process", times_limited, "times.")


def harvest():
    ## generate user id list from user2id output file
    users_to_follow = [int(line.rstrip('\n')) for line in open(sys.argv[1] + '.ids')]
    now = datetime.datetime.now()
    print("\nStarting tweet harvest at", now.strftime('%d-%m-%Y_%H:%M:%S'), "...")
    try: ## iterate through this list of ids.
        for user in users_to_follow:
            get_tweets(user)   ## get all their tweets and put into mongodb
       #     get_friends(user) ## this tends to rate limit, but tweet harvest doesn't (?!)
    except Exception as e:
        print(e)


############
## run it ##
############
if __name__ == "__main__":

    start_mongo_daemon()   ## check/start mongodb

    lookup_users()         ## get persistent user ids from screen names

    harvest()              ## get tweets for each user and archive in mongodb

    export()               ## create CSV ouput and backup mongodb

    report()               ## return some debug statistics

    stop_mongo_daemon()    ## close connection and shutdown mongodb

    now = datetime.datetime.now()
    print("\nAll done, twongo finished at", now.strftime('%d-%m-%Y_%H:%M:%S'))
    
