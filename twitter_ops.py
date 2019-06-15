import datetime
import os
import sys
import pymongo
import tweepy
from mongo_ops import index_mongo

def lookup_users(run_folder, screen_names, api, duplicate_users, not_found):

    """convert twitter screen names into persistent id numbers"""

    if '--refresh' not in sys.argv and os.path.exists(run_folder + "user_list.ids"):
        return
    with open(run_folder + "user_list") as file:
        lines = [x.strip() for x in file.readlines()]
        lines = [x for x in lines if x]
        for line in lines:
            if lines.count(line) > 1:
                duplicate_users.append(line)
    print(f"Converting user screen names to persistent id numbers...")
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
        if "--log" not in sys.argv:
            print(f"")

    # Write user codes to file.
    with open(run_folder + "user_list.ids", 'w') as id_file:
        for id in id_list:
            id_file.write("%s\n" % id)                            # write to id file
   

def get_tweets(twitter_id, db, api, collection, empty_users, private_users):

    """acquire tweets from each user id number and store them in MongoDB"""

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
            private_users.append(twitter_id)
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
                empty_users.append(twitter_id)
        except tweepy.TweepError as tweeperror:
            print(f"Not possible to acquire timeline of {twitter_id} : {tweeperror}")
            private_users.append(twitter_id)
        except tweepy.RateLimitError as rateerror:
            print(f"Rate limit reached, waiting for cooldown...")

    ## update the database with the acquired tweets for this user
    for tweet in alltweets:
        try:
            try:
                collection.update_one(tweet._json, {'$set': tweet._json}, upsert=True)
            except pymongo.errors.DuplicateKeyError:
                pass
        except IndexError:
            print(f"User {twitter_id} has no tweets to insert.")


def get_friends(twitter_id): ## get the "following" list for this user
    friend_list = []
    try:
        for friend in tweepy.Cursor(api.friends_ids, id = twitter_id, count = 200).pages():
            friend_list.extend(friend) # put the friends into a list
    except tweepy.RateLimitError as rateerror:
        print(f"Rate limit reached, waiting for cooldown... {rateerror}")
    try:
        for person in friend_list:     # insert those into a mongodb collection called "following"
            following_collection.update_one({"user_id": twitter_id}, {"$addToSet": {"following": [person]}}, upsert=True)
    except: # make this more specific?
        print(f"Problem putting friends into MongoDB...")


def harvest(run_folder, db, api, collection, empty_users, private_users, not_found, duplicate_users):
    index_counter = 0
    ## generate user id list from user2id output file
    users_to_follow = [int(line.rstrip('\n')) for line in open(run_folder + "user_list.ids")]
    now = datetime.datetime.now()
    print(f"\nStarting tweet harvest at {now.strftime('%H:%M:%S_%d-%m-%Y')} ...")
    try: ## iterate through this list of ids.
        for twitter_id in users_to_follow:
            if index_counter % 100 == 0: # every 100 users index the database
                index_mongo(run_folder, db)
            get_tweets(twitter_id, db, api, collection, empty_users, private_users)  ## get all their tweets and put into mongodb
            if '--getfriends' in sys.argv:
                get_friends(twitter_id) ## this tends to rate limit, but tweet harvest doesn't (?!)
            index_counter += 1
        print()
        if len(duplicate_users) > 0: # if users are not found, put into missing user file
            print(f"Info: {len(set(duplicate_users))} user names are duplicates (see user_list.duplicates)")
            with open(run_folder + "user_list.duplicates", 'w') as duplicate_user_file:
                for duplicate_user in set(duplicate_users):
                    duplicate_user_file.write("%s\n" % duplicate_user)    # write to missing user file
        if len(not_found) > 0: # if users are not found, put into missing user file
            print(f"Info: {len(not_found)} user names do not have accounts (see user_list.notfound)")
            with open(run_folder + "user_list.notfound", 'w') as missing_user_file:
                for missing_user in not_found:
                    missing_user_file.write("%s\n" % missing_user)    # write to missing user file
        if len(empty_users) > 0: # if users are empty, put into empty users file
            print(f"Info: {len(empty_users)} users have empty accounts (see user_list.empty)")
            with open(run_folder + "user_list.empty", 'w') as empty_user_file:
                for empty_user in empty_users:
                    empty_user_file.write("%s\n" % empty_user)    # write to empty user file  
        if len(private_users) > 0: # if users are private found, put into private user file
            print(f"Info: {len(private_users)} users have private accounts (see user_list.private)")
            with open(run_folder + "user_list.private", 'w') as private_user_file:
                for private_user in private_users:
                    private_user_file.write("%s\n" % private_user)    # write to private user file  

    except Exception as e:
        print(f"{e}")
