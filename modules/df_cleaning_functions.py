import json
import pandas as pd
import numpy as np
import re

def vader_df_2_geojson(df):

    """ Turns dataframe with text, location, vader scores into
    geojson with when, where, vader scores

    Incoming df from vader analysis has the fields:
    created_at place.full_name place.bounding_box.coordinates geo.coordinates
    text vader_neg vader_neu vader_pos vader_comp

    Writes a geojson with fields: NOPE THIS ISN'T FINISHED YET :)
    when, [vader scores], [relevant emoji given scores], where"""

    # Add latitude and longitude fields to dataframe
    df['lat'] = ""
    df['long'] = ""

    # If there is neither box or point geolocation
    if pd.isnull(df.loc[0, 'geo.coordinates']) and pd.isnull(df.loc[0, 'place.bounding_box.coordinates']):

        geo_coordinates = [''], [''] # make empty list

    # If there is only a bounding box, make a point location of the centre of the box
    elif pd.isnull(df.loc[0, 'geo.coordinates']):

        # regex out the box edges and average them to get pseudo point coordinates
        extract_geo_locs = re.findall(r"[-+]?\d*\.\d+|\d+", df.loc[0, 'place.bounding_box.coordinates'])
        box_edges = [float(i) for i in extract_geo_locs]
        geo_coordinates = [((box_edges[1] + box_edges[5]) / 2)], [((box_edges[0] + box_edges[4]) / 2)]

    # If there is point location, extract it
    else:
        # regex out the point location
        extract_geo_locs = re.findall(r"[-+]?\d*\.\d+|\d+", df.loc[0, 'geo.coordinates'])
        geo_coordinates = [float(i) for i in extract_geo_locs]

    # Insert geolocation into fields
    df.loc[0, 'lat'] = geo_coordinates[0]
    df.loc[0, 'long'] = geo_coordinates[1]

    # Remove unwanted columns
    df.drop(['place.full_name', 'geo.coordinates', 'place.bounding_box.coordinates', 'text'], axis=1, inplace=True)

    print(df) # DEBUG

    # Output a geojson from this refined dataframe
#    df.to_csv(output_filename, sep=',', encoding='utf-8')



def read_json(tweet_json_file):
    """Read in a .json file of tweets to a list of dictionaries"""

    #Initialise a list for the tweet json data to go in
    tweets = []

    #This is a function which is called during json.loads() to remove parts of the tweet object that
    #are assigned 'None' as their key value. This avoids a NoneType Error in the json_to_df function.
    def remove_nulls(d):
        return {k: v for k, v in d.items() if v is not None}

    #Read in the json data
    with open(tweet_json_file, errors='ignore') as f:
        for line in f:
            tweets.append(json.loads(line, object_hook=remove_nulls))

    #Return the list of tweets, which is a list of dictionaries - each dict is equivalent to the json obj
    return tweets


def json_to_df(data):

    """Take a json file of tweets, read them into a list and then save the desired columns to a Pandas dataframe"""

    #Use read_json function to create a list of dictionaries
    tweets = data

    #Now, create an empty dataframe with the columns we are interested in
    df = pd.DataFrame(columns=['tweet_id', 'created_at', 'user_id', 'user_loc', 'tweet_140', 'tweet_full',
                               'coords', 'place_name', 'bbox_coords', 'language'])

    #Append the relevant data from each Twitter JSON object as a row to the dataframe
    #N.B the .get(x, {}) is assigning a default empty dictionary if the .get returns no value, avoiding an error
    for tweet in tweets:
            df = df.append({
                'tweet_id' : tweet.get("id_str"), #id of tweet
                'created_at' : tweet.get("created_at"), #time/date stamp
                'user_id' : tweet.get("user").get("id_str"), #id of user
                'user_loc' : tweet.get("user").get("location"), #user's location on profile
                'tweet_140' : tweet.get("text"), #will always return, even for extended tweets
                'tweet_full' : tweet.get("extended_tweet", {}).get("full_text"), #will not always return
                'coords' : tweet.get("coordinates", {}).get("coordinates"), #will always return, null if relevant
                'place_name' : tweet.get("place", {}).get("full_name"), #will have 'Wales'
                'bbox_coords' : tweet.get("place", {}).get("bounding_box", {}).get("coordinates"), #bounding box for the location
                'language' : tweet.get("lang") #can address whether welsh or english
                }, ignore_index = True )
    return df


#Tidy the dataframe by consolidating the tweet text and the coordinates

def tidy_bbox(data, bbox_column_name):

    """Takes a Pandas dataframe with a column of bounding box values and calculates the midpoint, or using coords
    if no bounding box, and adds the lat and long to their own columns"""

    #Initialise new columns for lat and long
    data['lat'] = ""
    data['long'] = ""

    #Use 'keep'' to get where the coords column is null - this is where we will need to calculate the center of the bbox.
    keep = pd.isnull(data['geo.coordinates'])
    data_valid = data[keep]

    #Use the keep-data find the bbox midpoint on only those elements which meet the keep condition
    data.loc[keep, 'lat'] = data_valid[bbox_column_name].apply(lambda el: (el[0][0][1] + el[0][2][1])/2)
    data.loc[keep, 'long'] = data_valid[bbox_column_name].apply(lambda el: (el[0][0][0] + el[0][2][0])/2)


    #redefine the masked data to get where coords has data in
    data_valid = data[~keep]
    #Reverse the mask to fetch the coords and fill the rest of the lat/long columns
    data.loc[~keep, 'lat'] = data_valid[bbox_column_name].apply(lambda el: el[1])
    data.loc[~keep, 'long'] = data_valid[bbox_column_name].apply(lambda el: el[0])

    return data


#Tidy the text since the extended tweets and the shorter length tweets are in two different columns.

def tidy_text_cols(data):

    """ Uses values from the short ('tweet_140') and extended ('tweet_full') columns to make a single 'tweet_text' column with the
    full version of every tweet. """

    #Initialise new column
    data['tweet_text'] = ""

    #keep the data for where 'tweet_full' is not used
    keep = pd.isnull(data['tweet_full'])

    #Where tweet_full is empty, make tweet_140 the text
    data_valid = data[keep]
    data.loc[keep, 'tweet_text'] = data_valid['tweet_140']

    #Where tweet_full is used, make tweet_full as the text
    data_valid = data[~keep]
    data.loc[~keep, 'tweet_text'] = data_valid['tweet_full']

    return data


def parse_datetime(data):

    """ Reads Twitter's 'created at' and parses it to a Python datetime object in a new column called 'date_time' """

    from datetime import datetime
    from dateutil.parser import parse

    #parse the created_at value to python custom date_time object
    data.loc['date_time'] = data['created_at'].apply(lambda el: parse(el))


def read_and_tidy(tweet_json_file):

    """ Given a json file of tweets, will import into a pd.df and tidy the text, coordinates and date_time objects """

    data = read_json(tweet_json_file)
    data = json_to_df(data)
    data = tidy_bbox(data)
    data = tidy_text_cols(data)
    data = parse_datetime(data)
    return data
