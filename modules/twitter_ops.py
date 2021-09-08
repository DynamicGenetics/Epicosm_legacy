
#~ Standard library imports
import os
import sys
import time
import re
import json
import subprocess

#~ 3rd party imports
import pymongo
import requests
from requests.exceptions import *
from retry import retry
from alive_progress import alive_bar

#~ Local application imports
try:
    import bearer_token
except ModuleNotFoundError as e:
    print("Your bearer_token.py doesn't seem to be here.")
    sys.exit(1)

bearer_token = bearer_token.token


def bearer_oauth(r):

    """
    Set up Oauth object.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2FullArchiveSearchPython"

    return r


@retry(RequestException, delay=1, backoff=5, max_delay=900)
def connect_to_endpoint(url, params):

    """
    Make connection to twitter endpoint

    CALLS:  requests.request()

    ARGS:   url: the full URL built by create_url, completed with
            params (usually the fields you want). If you are doing
            a user lookup, params aren't needed and can be left empty.

    RETS:   response from the endpoint as json
    """

    response = requests.request("GET", url, auth=bearer_oauth, params=params)
    if response.status_code == 429:
        print(f"Rate limited, waiting for cooldown...")
        raise RequestException
    if response.status_code == 401:
        print("Bearer token was not verified. Please check and retry.")
        sys.exit(129)
    if response.status_code == 503:
        print("Twitter's servers seem unavailable, giving them a moment...")
        raise RequestException
    elif response.status_code != 200:
        print("Didn't get a 200 response:", response.status_code)
    return response.json()


def create_url(screen_names):

    """
    Builds the URL for requesting multiple user details.

    ARGS: a comma separated string of names, coming from user_list
    RETS: the formatted complete URL as a query
    """

    #~ format the incoming string as URL
    usernames = f"usernames={screen_names}"
    #~ specify the fields we would like returned
    user_fields = "user.fields=id,username,name,created_at,description,location,pinned_tweet_id,public_metrics"
    #~ stick it all together
    url = f"https://api.twitter.com/2/users/by?{usernames}&{user_fields}"

    return url


def chunks(l, n):

    """split things into manageable blocks"""

    for i in range(0, len(l), n):
        yield l[i:i+n]


def user_lookup_v2():

    """
    Takes a text file with one twitter username per line,
    queries twitter with these as blocks of 100 (the maximum),
    and write out a file of the user details as json.

    CALLS:  create_url()
            connect_to_endpoint()
    """

    with open("user_list", "r") as infile: #~ clean up user_list
        users = [x.strip() for x in infile.readlines()]  #~ whitespace strip
        users = [x for x in users if x != ""]            #~ empty line removal
        users = [(re.sub(r"^@", r"", x)) for x in users] #~ clean "@s" on twitter handles
        #~ names < 3 chars are an error
        user_errors = [x for x in users if len(x) < 3]
        users = [x for x in users if len(x) > 2]
        #~ names > 15 chars are an error
        user_errors = user_errors + [x for x in users if len(x) > 15]
        users = [x for x in users if len(x) <= 15]
        #~ names with non-standard chars are an error
        user_errors = user_errors + [x for x in users if not re.match("^[a-zA-Z0-9_]*$", x)]
        users = [x for x in users if re.match("^[a-zA-Z0-9_]*$", x)]
        if len(user_errors) > 0:
            print(f"Some usernames in user_list were invalid: {user_errors}.")

    with open("user_details.json", "w") as outfile, open("user_errors.json", "w") as errorfile:
        print(f"Looking up {len(users)} user details.")
        json_array = []
        json_errors = []
        for chunk in list(chunks(users, 100)): #~ split list into manageable chunks of 100
            comma_separated_string = ",".join(chunk) #~ lookup takes a comma-separated list
            url = create_url(comma_separated_string)
            json_response = connect_to_endpoint(url, params="")
            for result in json_response["data"]: #~ I know this looks a little crazy
                json_array.append(result)  #~ but I couldn't find another way to preserve
            if "errors" in json_response:
                for no_result in json_response["errors"]: #~ sane json nesting :/
                    json_errors.append(no_result)
        outfile.write(json.dumps(json_array, indent=4, sort_keys=True))
        errorfile.write(json.dumps(json_errors, indent=4, sort_keys=True))


def request_timeline_response(twitter_id, timeline_params):

    """
    OK so this function tries to catch lots of things so looks a bit crazy.
    Using the timeline parameters built by the loop, gets the timeline of
    a twitter id.

    CALLS:  connect_to_endpoint()

    ARGS:   the built timeline_url for API endpoint,
            timeline_parameters (what fields, how many, most recent),
            the ID number for the user.

    RETS:   hopefully, the timeline response as a JSON,
            OR 1 if there was an issue. Return value 1 is
            used as a trigger for the continue in the loop.
    """

    timeline_url = "https://api.twitter.com/2/tweets/search/all"

    try:

        timeline_response = connect_to_endpoint(timeline_url, timeline_params)

        if timeline_response["meta"]["result_count"] == 0:
            print(f"No new tweets for {twitter_id}.")
            return 1 #~ all "return 1"s are triggers to continue the harvest loop

        if "errors" in timeline_response:
            print(f"Problem on {twitter_id} :", timeline_response["title"])
            return 1

        #~ each subfield in "data" is a tweet / following.
        if "data" not in timeline_response:
            print(f"No data in response: {api_response}")
            return 1

        return timeline_response

    except RequestException:
        print(f"Rate limited even after cooldown on {twitter_id}. Moving on...")
        return 1

    except Exception as e:
        print(f"Something went wrong on {twitter_id}: {e}")
        return 1


def timeline_harvest_v2(db, collection):

    """
    This is the main running function for the harvester,
    using the Twitter v2 API and the api.twitter.com/2/tweets/search/all
    endpoint - if you don't have an academic authorised bearer token,
    this will not work. (Standard level access is to
    api.twitter.com/2/tweets/search/recent)

    1.  Takes the user_details as a list of ids to loop through
    2.  Checks if the DB has this user, or what the newest harvested
        tweet ID is.
    3.  Harvests from the newest tweet, or as old as possible if new.
    4.  Inserts the response from the API to the DB, in batches of 500.

    CALLS:  request_timeline_response()
            insert_to_mongodb()
            json.load()
            collection.count_documents()
            collection.find_one()

    ARGS:   db name (set in epicosm.py, just as local defaults)
            collection name (set in epicosm.py)
    """

    with open("user_details.json", "r") as infile:
        #~ load in the json of users
        user_details = json.load(infile)

        total_users = (len(user_details))
        print(f"\nHarvesting timelines from {total_users} users...")

        #~ loop over each user ID
        for user in user_details:

            twitter_id = user["id"]

            #~ check if we have this user in DB
            if collection.count_documents({"author_id": twitter_id}) == 0:
                latest_tweet = 1 #~ go as far back in time as possible.
            else: #~ find latest tweet existing in collection
                #~ I know this looks bonkers, but pymongo cannot alphanumeric sort (afaik)
                tweet_ids = list(collection.find({"author_id": twitter_id}, {"id": 1}))
                tweet_id_extract = []
                for i in tweet_ids:
                    tweet_id_extract.append(int(i["id"]))
                latest_tweet = max(tweet_id_extract)

            timeline_params = {
                "query": f"(from:{twitter_id})",
                "tweet.fields": "id,author_id,created_at,text,public_metrics,attachments,geo",
                "max_results": 500,
                "since_id": latest_tweet}

            #~ send the request for the first 500 tweets and insert to mongodb
            print(f"Requesting timeline for user {twitter_id}...")
            api_response = request_timeline_response(twitter_id, timeline_params)
            if api_response == 1: #~ this "1" is an end-trigger from request_timeline_response
                user_tweet_count = collection.count_documents({"author_id": twitter_id})
                print(f"Tweet count for user {twitter_id} in DB: {user_tweet_count}")
                continue
            else:
                insert_to_mongodb(api_response, collection)

            #~ we get a "next_token" if there are > 500 tweets.
            try:
                while "next_token" in api_response["meta"]:
                    timeline_params["next_token"] = api_response["meta"]["next_token"]
                    api_response = request_timeline_response(twitter_id, timeline_params)
                    if api_response == 1: #~ "1" means "next"
                        continue
                    else:
                        insert_to_mongodb(api_response, collection)
            except TypeError as e:
                print(e)
                pass #~ move on for this harvest iteration.

            user_tweet_count = collection.count_documents({"author_id": twitter_id})
            print(f"Tweet count for user {twitter_id} in DB: {user_tweet_count}")

    users_in_collection = len(collection.distinct("author_id"))
    print(f"\nThe DB contains a total of {collection.count()} tweets from {users_in_collection} users.")


def following_list_harvest(db, collection):

    """
    Builds the URL for requesting the user's following list,
    and sends it to the Twitter API v2.

    ARGS: the name of the following collection, taken from env,
          DB name
    """

    with open("user_details.json", "r") as infile:
        #~ load in the json of users
        user_details = json.load(infile)

        total_users = (len(user_details))
        print(f"\nHarvesting following lists from {total_users} users...")

        #~ we need a compound index here, since two people can follow the same user
        #~ so, records where BOTH follower_id and id are the same are considered duplicates
        collection.create_index([
            ("follower_id", pymongo.ASCENDING),
            ("id", pymongo.ASCENDING)], unique=True, dropDups=True)

        #~ loop over each user ID
        for user in user_details:

            params = {"max_results": 1000}
            twitter_id = user["id"]
            url = f"https://api.twitter.com/2/users/{twitter_id}/following?"

            print(f"Requesting {twitter_id} following list...")
            api_response = request_api_response(twitter_id, url, params)

            #~ request first 1000 followings
            if api_response == 1: #~ finished user, moving to next one
                print(twitter_id, "followings count in DB:", following.count())
                continue
            else:
                #~ assign new field with who we are harvesting to each following
                for following_item in api_response["data"]:
                    following_item["follower_id"] = twitter_id
                insert_to_mongodb(api_response, collection)

            #~ we get a "next_token" if there are > 1000 followings.
            try:
                while "next_token" in api_response["meta"]:
                    params["pagination_token"] = api_response["meta"]["next_token"]
                    api_response = request_api_response(twitter_id, url, params)
                    if api_response == 1: #~ "1" means "next"
                        continue
                    else:
                        #~ assign new field with who we are harvesting to each following
                        for following_item in api_response["data"]:
                            following_item["follower_id"] = twitter_id
                        insert_to_mongodb(api_response, collection)

            except TypeError:
                pass #~ api_response returned "1", so all done.

            print(twitter_id, "followings count in DB:", collection.count_documents({"follower_id": twitter_id}))

    users_in_collection = len(collection.distinct("follower_id"))
    print(f"\nThe DB contains a total of {collection.count()} followings from {users_in_collection} users.")


def insert_to_mongodb(api_response, collection):

    """
    Puts tweets into the MongoDB database collection. I'm not sure if I am doing
    this right, as "insert_one" loop seems silly? But I can't get "insert many"
    to work.

    CALLS:  collection.insert_one()

    ARGS:   Stuff that the API sent back after query,
            the name of the collection.

    RETS:   Nothing, puts things into DB.
    """

    for record in api_response["data"]:

        try:
            collection.insert_one(record)
        except pymongo.errors.DuplicateKeyError:
            pass #~ denies duplicates being added