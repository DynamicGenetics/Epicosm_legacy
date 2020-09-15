import datetime
import os
import sys
import pymongo
import tweepy
import time


def get_credentials():

    credentials = {}
    try:
        with open("credentials.txt") as file:
            for line in file:
                line = line.strip()  # remove errant whitespace
                if line and not line.startswith("#"): # take the non-commented lines
                    try:
                        key, val = line.split()
                        if val:
                            credentials[key.upper()] = val
                    except ValueError: # users might have forgotten to update the credentials template file
                        print("Your credentials.txt file doesn't look complete.")
                        sys.exit(0) 
    except FileNotFoundError:
        print("Your credentials.txt file doesn't seem to exist here.")
        sys.exit(0)
    # verify the given credentials
    auth = tweepy.OAuthHandler(credentials["CONSUMER_KEY"], credentials["CONSUMER_SECRET"])
    auth.set_access_token(credentials["ACCESS_TOKEN"], credentials["ACCESS_TOKEN_SECRET"])
    api = tweepy.API(auth)
    try:
        api.verify_credentials()
        print("Credentials verified by Twitter...")
    except:
        print("Your credentials were not verified - please check them and retry.")
        sys.exit(0)
    return credentials, auth, api


def lookup_users(run_folder, screen_names, credentials, auth, api):

    """convert twitter screen names into persistent id numbers"""

    duplicate_users = []
    not_found = []

    if "--refresh" not in sys.argv and os.path.exists(run_folder + "/user_list.ids"):
        return

    with open(run_folder + "/user_list") as file:
        lines = [x.strip() for x in file.readlines()]
        lines = [x for x in lines if x]
        for line in lines:
            if lines.count(line) > 1:
                duplicate_users.append(line)

    # Write duplicate users to file.
    if len(duplicate_users) > 0:
        print(f"Info: {len(set(duplicate_users))} user names are duplicates (see user_list.duplicates)")
        with open(run_folder + "/user_list.duplicates", 'w') as duplicate_file:
            for duplicate in duplicate_users:
                duplicate_file.write("%s\n" % duplicate)

    print(f"Converting user screen names to persistent id numbers...")
 
    # Count the number of screen names in the input file
    non_blank_count = 0
    with open(run_folder + "/user_list") as count_file:
        for line in count_file:
            if line.strip():
                non_blank_count += 1

    # chunks splits the screen_name list into manageable blocks:
    def chunks(l, n):
        # For item i in a range that is a length of l,
        for i in range(0, len(l), n):
            # Create an index range for l of n items:
            yield l[i:i+n]

    # Query twitter with the comma separated list
    id_list = []        # empty list for id to go into
    for chunk in list(chunks(screen_names, 42)): # split list into manageable chunks of 42
        comma_separated_string = ",".join(chunk) # lookup takes a comma-separated list
        for user in chunk:
            try:
                user = api.get_user(screen_name = user) 
                id_list.append(user.id) # get the id and put it in the id_list
    
            except tweepy.error.TweepError as e:
                not_found.append(user) # if not found, put user in not found list

    # Write user codes to file.
    with open(run_folder + "/user_list.ids", 'w') as id_file:
        for id in id_list:
            id_file.write("%s\n" % id)

    # Write non-found users to file.
    if len(not_found) > 0:
        print(f"Info: {len(set(not_found))} users were not found (see user_list.not_found)")
        with open(run_folder + "/user_list.not_found", 'w') as not_found_file:
            for not_found_user in not_found:
                not_found_file.write("%s\n" % not_found_user)


def get_tweets(run_folder, twitter_id, empty_users, private_users,
               credentials, auth, api, client, db, collection):

    """acquire tweets from each user id number and store them in MongoDB"""

    # check if this user history has been acquired
    if db.tweets.count_documents({"user.id": twitter_id}) > 0:
        # we already have this user's timeline, just get recent tweets
        try:
            print(f"User {twitter_id} is in the database, normal acquisition cycle...")
            alltweets = []
            new_tweets = api.user_timeline(id=twitter_id, count=200,
                                           tweet_mode='extended', exclude_replies=True,
                                           wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
            alltweets.extend(new_tweets)
        except tweepy.TweepError as e:
            print(f"Not possible to acquire timeline of {twitter_id} : {e}")
    else:
        # this user isn't in database: get <3200 tweets if possible
        try:
            print(f"User {twitter_id} is new, deep acquisition cycle...")
            alltweets = []
            new_tweets = api.user_timeline(id=twitter_id, count=200,
                                           tweet_mode="extended", exclude_replies=True,
                                           wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
            alltweets.extend(new_tweets) # this gets the first 200 (maximum per request)
            
            try:
                oldest = alltweets[-1].id - 1 # this is now the oldest tweet
                while len(new_tweets) > 0: # so we do it again, going back another 200 tweets
                    new_tweets = api.user_timeline(id=twitter_id, count=200, max_id=oldest,
                                                   tweet_mode="extended", exclude_replies=True,
                                                   wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
                    alltweets.extend(new_tweets)
                    oldest = alltweets[-1].id - 1 # this is now the oldest tweet
            
            except IndexError: # Index error indicates an empty account.
                print(f"Empty timeline for user {twitter_id} : skipping.")
                empty_users.append(twitter_id)
        except tweepy.TweepError as e:
            print(f"Not possible to acquire timeline of {twitter_id} : {e}")
        except tweepy.ConnectionResetError as e:
            print(f"Connection was reset during tweet harvest on {twitter_id}: {e}")
        except tweepy.RateLimitError as e: # Twitter telling us to chill out
            print(f"Rate limit reached on {twitter_id}, waiting for cooldown...")

    return alltweets


def insert_to_mongodb(alltweets, collection):

    # update the database with the acquired tweets for this user
    for tweet in alltweets:
            try:
                try:
                    collection.insert_one(tweet._json, {"$set": tweet._json})
                except pymongo.errors.DuplicateKeyError:
                    pass # denies duplicates being added
            except IndexError:
                print(f"User {twitter_id} has no tweets to insert.")


def get_friends(run_folder, credentials, auth, api, friend_collection):

    """Get the friend list and put it in MongoDB"""

    def ask_api_for_friend_list():
        try:
            for friend in tweepy.Cursor(api.friends_ids, id = twitter_id, count = 5000,
                                        wait_on_rate_limit=True, wait_on_rate_limit_notify=True,
                                        retry_count = 3, timeout = 30).pages():
                friend_list.extend(friend)
            print(f"Friends (following) list of {twitter_id} acquired.") 
        except tweepy.TweepError as e:
            print(f"There was a problem gathering friends of {twitter_id}: {e}")


    users_to_get_friends = [int(line.rstrip("\n")) for line in open(run_folder + "/user_list.ids")]

    print(f"Getting friend lists of users...")
    for twitter_id in users_to_get_friends:
        try_count = 0
        friend_list = []
        ask_api_for_friend_list()
        
        # insert to MongoDB
        try:
            for friend in friend_list:     # insert those into a mongodb collection called "friends"
                friend_collection.update_one({"user_id": twitter_id}, {"$addToSet": {"friends": [friend]}}, upsert=True)
        except Exception as e:
            print(f"Problem putting friend list into MongoDB: {e}")


def harvest(run_folder, credentials, auth, api, client, db, collection):

    """Get tweet timelines and insert new tweets into MongoDB"""

    empty_users = []
    private_users = []
    users_to_follow = [int(line.rstrip("\n")) for line in open(run_folder + "/user_list.ids")]
    now = datetime.datetime.now()
    print(f"Starting tweet harvest at {now.strftime('%Y-%m-%d_%H:%M:%S')} ...")
    try: ## iterate through this list of ids.
        for twitter_id in users_to_follow:
            alltweets = get_tweets(run_folder, twitter_id, empty_users, private_users,
                                   credentials, auth, api, client, db, collection)
            insert_to_mongodb(alltweets, collection)

        if len(empty_users) > 0: # if empty accounts, put into empty users file
            print(f"Info: {len(empty_users)} users have empty accounts (see user_list.empty)")
            with open(run_folder + "/user_list.empty", "w") as empty_user_file:
                for empty_user in empty_users:
                    empty_user_file.write("%s\n" % empty_user)    # write to empty user file

        if len(private_users) > 0: # if private accounts found, put into private user file
            print(f"Info: {len(private_users)} users have private accounts (see user_list.private)")
            with open(run_folder + "/user_list.private", "w") as private_user_file:
                for private_user in private_users:
                    private_user_file.write("%s\n" % private_user)    # write to private user file

    except Exception as e:
        print(f"Something went wrong during harvest: {e}")

