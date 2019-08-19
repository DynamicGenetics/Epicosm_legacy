import datetime
import os
import sys
import pymongo
import tweepy

def lookup_users(run_folder, screen_names, api):

    """convert twitter screen names into persistent id numbers"""

    duplicate_users = []
    not_found = []
    if '--refresh' not in sys.argv and os.path.exists(run_folder + "user_list.ids"):
        return
    with open(run_folder + "user_list") as file:
        lines = [x.strip() for x in file.readlines()]
        lines = [x for x in lines if x]
        for line in lines:
            if lines.count(line) > 1:
                duplicate_users.append(line)
    
    # Write duplicate users to file.
    if len(duplicate_users) > 0:
        print(f"Info: {len(set(duplicate_users))} user names are duplicates (see user_list.duplicates)")
        with open(run_folder + "user_list.duplicates", 'w') as duplicate_file:
            for duplicate in duplicate_users:
                duplicate_file.write("%s\n" % duplicate)
    
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
            id_file.write("%s\n" % id)

    # Write non-found users to file.
    if len(not_found) > 0:
        print(f"Info: {len(set(not_found))} users were not found (see user_list.not_found)")
        with open(run_folder + "user_list.not_found", 'w') as not_found_file:
            for not_found_user in not_found:
                not_found_file.write("%s\n" % not_found_user)
   

def get_tweets(run_folder, twitter_id, db, api, collection, empty_users, private_users):

    """acquire tweets from each user id number and store them in MongoDB"""

    ## check if this user history has been acquired
    if db.tweets.count_documents({"user.id": twitter_id}) > 0:
        ## we already have this user's timeline, just get recent tweets
        try:
            print(f"User {twitter_id} is in the database, normal acquisition cycle...")
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
                    collection.insert_one(tweet._json, {'$set': tweet._json})
                except pymongo.errors.DuplicateKeyError:
                    pass # denies duplicates being added
            except IndexError:
                print(f"User {twitter_id} has no tweets to insert.")


def get_following(api, run_folder, following_collection):

    """Get the following list and put it in MongoDB"""
    print(f"\nGetting following lists of users...")
    following_list = []
    users_to_follow = [int(line.rstrip('\n')) for line in open(run_folder + "user_list.ids")]
    for twitter_id in users_to_follow:
        try:
            for following in tweepy.Cursor(api.friends_ids, id = twitter_id, count = 200).pages():
                following_list.extend(following) # put followings into a list
        except tweepy.RateLimitError as rateerror:
            print(f"Rate limit reached, waiting for cooldown... {rateerror}")
        try:
            for person in following_list:     # insert those into a mongodb collection called "following"
                following_collection.update_one({"user_id": twitter_id}, {"$addToSet": {"following": [person]}}, upsert=True)
        except Exception as e: # make this more specific?
            print(f"Problem putting following list into MongoDB...")
            print(e)

def harvest(run_folder, db, api, collection):

    """Get tweet timelines and insert new tweets into MongoDB"""

    empty_users = []
    private_users = []
    users_to_follow = [int(line.rstrip('\n')) for line in open(run_folder + "user_list.ids")]
    now = datetime.datetime.now()
    print(f"\nStarting tweet harvest at {now.strftime('%H:%M:%S_%d-%m-%Y')} ...")
    try: ## iterate through this list of ids.
        for twitter_id in users_to_follow:
            get_tweets(run_folder, twitter_id, db, api, collection, empty_users, private_users)

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

          
         
