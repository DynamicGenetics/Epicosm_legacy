import requests
import os
import time
from retry import retry
import json

# To set your environment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
# bearer_token = os.environ.get("BEARER_TOKEN")
bearer_token = "XXXXXXX"

search_url = "https://api.twitter.com/2/tweets/search/all"

# Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
# expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields
# query_params = {'query': '(from:twitterdev -is:retweet) OR #twitterdev','tweet.fields': 'author_id'}
query_params = {"query": "(from:XXXXXXXX)",
                "tweet.fields": "attachments,author_id,created_at,public_metrics",
                "max_results": 500,
                "since_id": 1}


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2FullArchiveSearchPython"

    return r


@retry(Exception, tries=3, delay=3, backoff=5)
def connect_to_endpoint(url, params):

    response = requests.request("GET", search_url, auth=bearer_oauth, params=params)
    print(response.status_code)
    if response.status_code == 429:
        raise Exception("Rate limited")
    if response.status_code != 200:
        raise Exception("Didn't get a 200 response...")
    return response.json()


def main():

    json_response = connect_to_endpoint(search_url, query_params)
    print(json.dumps(json_response, indent=4, sort_keys=True))
    while "next_token" in json_response["meta"]:
        query_params["next_token"] = json_response["meta"]["next_token"]
        json_response = connect_to_endpoint(search_url, query_params)
        print(json.dumps(json_response, indent=4, sort_keys=True))


if __name__ == "__main__":
    main()

