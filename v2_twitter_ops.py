import requests
from requests.exceptions import *
import os
import sys
import pymongo
import subprocess
import time
from retry import retry
import json
from alive_progress import alive_bar

#~ your bearer token will need to be in the local file
#~ "bearer_token.py", see readme for details.
import bearer_token
bearer_token = bearer_token.token

#! to do
#! stress test
#! search to check all are going in
#! (eg, why was it getting 639 when it should be 640 on my own a/c?)
#! also, check other lost tweets
#! put v2_twitter_ops in the right place. remove redundancy.

def bearer_oauth(r):

    """
    Set up Oauth object.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2FullArchiveSearchPython"

    return r


@retry(RequestException, tries=6, delay=5, backoff=3)
def connect_to_endpoint(url, params):

    """
    Make connection to twitter endpoint

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
    elif response.status_code != 200:
        print("Didn't get a 200 response:", response.status_code)
    return response.json()


def create_url(screen_names):

    """
    Builds the URL of the endpoint that we want to make a request from

    ARGS: a comma separated string of names, coming from user_list

    RETS: the formatted complete URL as a query
    """

    #~ format the incoming string as URL
    usernames = "usernames={}".format(screen_names)
    #~ specify the fields we would like returned
    user_fields = "user.fields=id,username,name,created_at,description,location,pinned_tweet_id,public_metrics"
    #~ stick it all together
    url = "https://api.twitter.com/2/users/by?{}&{}".format(usernames, user_fields)

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
    """

    with open("user_list", "r") as infile:
        users = [x.strip() for x in infile.readlines()]
        #~ erroneous names > 15 chars needs removing
        users = [x for x in users if x if len(x) <= 15]

    with open("user_details.json", "w") as outfile:
        print(f"Looking up {len(users)} user details")
        for chunk in list(chunks(users, 100)): # split list into manageable chunks of 100
            comma_separated_string = ",".join(chunk) # lookup takes a comma-separated list
            url = create_url(comma_separated_string)
            json_response = connect_to_endpoint(url, params="")
            outfile.write(json.dumps(json_response, indent=4, sort_keys=True))


def request_timeline(timeline_url, timeline_params, twitter_id):
    try:
        timeline_response = connect_to_endpoint(timeline_url, timeline_params)
        if timeline_response["meta"]["result_count"] == 0:
            print(f"No new tweets for {twitter_id}.")
            return 1 #~ all "return 1"s are triggers to continue the harvest loop
        if "errors" in timeline_response:
            print(f"Problem on {twitter_id} :", timeline_response["title"])
            return 1
        #~ each subfield in "data" is a tweet.
        if "data" not in timeline_response:
            print(f"No data in response: {timeline_response}")
            return 1
        return timeline_response
    except RequestException:
        print(f"Hmm, rate limited on {twitter_id} even after waiting. Moving on.")
        return 1
    except Exception as e:
        print(f"Something went wrong on {twitter_id}: {e}")
        return 1


def insert_timeline_to_mongodb(timeline_response, collection):
    for tweet in timeline_response["data"]:
        try:
            collection.insert_one(tweet)
        except pymongo.errors.DuplicateKeyError:
            pass #~ denies duplicates being added


def timeline_harvest_v2(db, collection):

    """
    Queries the 2/tweets/search/all endpoint for tweets from a user.
    You will need access to the "all" endpoint to use this - ie have
    an academic approved account. Be wary of the "id" variables and
    fields here - they can get confusing.

    ARGS: none.

    RETS: none. Inserts new tweets to DB.
    """

    timeline_url = "https://api.twitter.com/2/tweets/search/all"

    with open("user_details.json", "r") as infile:
        #~ load in the json of users
        user_details = json.load(infile)

        total_users = (len(user_details["data"]))
        print(f"Harvesting from {total_users} users...")

        #~ loop over each user ID
        for user in user_details["data"]:

            twitter_id = user["id"]

            #~ check if we have this user, or get latest tweet id if we do.
            if collection.count_documents({"author_id": twitter_id}) == 0:
                latest_tweet = 1 #~ go as far back in time as possible.
            else:
                latest_tweet = collection.find_one(
                    {"author_id": twitter_id},
                    sort=[("id", pymongo.DESCENDING)])["id"]

            print(f"Requesting {twitter_id} timeline...")
            timeline_params = {
                "query": f"(from:{twitter_id})",
                "tweet.fields": "id,author_id,created_at,text,public_metrics,attachments,geo",
                "max_results": 500,
                "since_id": latest_tweet}

            #~ send the request for the first 500 tweets and insert to mongodb

            timeline_response = request_timeline(timeline_url, timeline_params, twitter_id)
            if timeline_response == 1:
                continue
            else:
                insert_timeline_to_mongodb(timeline_response, collection)

            #~ we get a "next_token" if there are > 500 tweets.
            loop = 1
            try:
                while "next_token" in timeline_response["meta"]:
                    timeline_params["next_token"] = timeline_response["meta"]["next_token"]
                    print(timeline_params)
                    # try:
                    timeline_response = request_timeline(timeline_url, timeline_params, twitter_id)
                    print(timeline_response["meta"])
                    if request_timeline(timeline_url, timeline_params, twitter_id) == 1:
                        continue
                    else:
                        insert_timeline_to_mongodb(timeline_response, collection)
                    print(loop)
                    loop += 1
            except TypeError:
                pass #~ timeline_response return == 1, so all done.

            print(twitter_id, "tweet NOW count in DB =", collection.count_documents({"author_id": twitter_id}))

    print(f"The DB contains a total of {collection.count()} tweets from {total_users} users.")

