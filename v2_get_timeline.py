import requests
from requests.exceptions import *
import os
import sys
import subprocess
import time
from retry import retry
import json

#~ your bearer token will need to be in the local file
#~ "bearer_token.py", see readme for details.
import bearer_token
bearer_token = bearer_token.token
#! to do
#! - make consistent with mongoimport
#! - test run - do you get limited? blocked?!


def bearer_oauth(r):

    """
    Set up Oauth object.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2FullArchiveSearchPython"

    return r


@retry(RequestException, tries=5, delay=5, backoff=3)
def connect_to_endpoint(url, params):

    response = requests.request("GET", url, auth=bearer_oauth, params=params)
    if response.status_code == 429:
        print(f"Rate limited, waiting for cooldown...")
        raise RequestException
    if response.status_code == 401:
        print("Bearer token was not verified. Please check and retry.")
        sys.exit(129)
    elif response.status_code != 200:
        print("Didn't get a 200 response:", response.status_code)
    else:
        print(response.status_code)
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

    """ split things into manageable blocks"""

    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i+n]


def main():

    # # # with open("user_list", "r") as infile:
    # # #     users = [x.strip() for x in infile.readlines()]
    # # #     users = [x for x in users if x]

    # # # with open("user_details.json", "w") as outfile:
    # # #     for chunk in list(chunks(users, 100)): # split list into manageable chunks of 100
    # # #         comma_separated_string = ",".join(chunk) # lookup takes a comma-separated list
    # # #         url = create_url(comma_separated_string)
    # # #         json_response = connect_to_endpoint(url, params="")
    # # #         outfile.write(json.dumps(json_response, indent=4, sort_keys=True))
    # # #         print(json.dumps(json_response, indent=4, sort_keys=True))

# Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
# expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields
# timeline_params = {'query': '(from:twitterdev -is:retweet) OR #twitterdev','tweet.fields': 'author_id'}
    timeline_url = "https://api.twitter.com/2/tweets/search/all"

    with open("user_details.json", "r") as infile:
        #~ load in the json of users
        user_details = json.load(infile)

        #~ loop over each user ID
        for user in user_details["data"]:
            id = user["id"]
            timeline_params = {"query": f"(from:{id})",
                               "tweet.fields": "attachments,author_id,created_at,public_metrics",
                               "max_results": 500,
                               "since_id": 1}

            #~ send the request for the first 500 tweets
            try:
                timeline_response = connect_to_endpoint(timeline_url, timeline_params)
            except RequestException:
                print("Hmm, rate limited even after waiting. Moving on.")
                continue

            with open(id + ".json", "w") as outfile:

                outfile.write(json.dumps(timeline_response, indent=4, sort_keys=True))

                #~ repeat asking for 500 more until "next_token" doesn't exist.
                while "next_token" in timeline_response["meta"]:

                    timeline_params["next_token"] = timeline_response["meta"]["next_token"]

                    try:
                        timeline_response = connect_to_endpoint(timeline_url, timeline_params)
                    except RequestException:
                        print("Hmm, rate limited even after waiting. Moving on.")
                        continue

                    outfile.write(json.dumps(timeline_response, indent=4, sort_keys=True))


if __name__ == "__main__":

    main()

