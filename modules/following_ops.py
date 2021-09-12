
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


def request_following_list(twitter_id, url):

    """
    This is a modification of the request_timeline_response in twitter ops.
    The params are a little different, and making a generalised version was getting messy
    and error prone.

    CALLS:  connect_to_endpoint()

    ARGS:   the ID number for the user.
            the built url for API endpoint.

    RETS:   the following list response as a JSON,
            OR 1 if there was an issue. Return value 1 is
            used as a trigger for the continue in the loop.
    """

    params = {"max_results": 1000}

    try:

        following_response = connect_to_endpoint(url, params)

        if following_response["meta"]["result_count"] == 0:
            print(f"No followings for {twitter_id}.")
            return 1 #~ all "return 1"s are triggers to continue the harvest loop

        if "errors" in following_response:
            print(f"Problem on {twitter_id} :", following_response["title"])
            return 1

        #~ each subfield in "data" is a tweet / following.
        if "data" not in following_response:
            print(f"No data in response: {api_response}")
            return 1

        return following_response

    except RequestException:
        print(f"Rate limited even after cooldown on {twitter_id}. Moving on...")
        return 1

    except Exception as e:
        print(f"Something went wrong on {twitter_id}: {e}")
        return 1


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

            twitter_id = user["id"]
            url = f"https://api.twitter.com/2/users/{twitter_id}/following?"

            print(f"Requesting {twitter_id} following list...")
            api_response = request_following_list(twitter_id, url)

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