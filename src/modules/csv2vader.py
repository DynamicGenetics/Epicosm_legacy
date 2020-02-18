import pandas as pd
from pandas import DataFrame
import numpy as np
import json
import sys
import os
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import df_cleaning_functions


# Set up the dataframe by importing tweet.csv and setting up columns
def set_up_dataframe(csv_file):

    """ Build a dataframe with a tweet for each row.

    Rows are tweets, columns are time tweeted to the day,
    we add append word count"""

    # the read_csv engine must be python, not default of c, or some lines will mess with it
    df = DataFrame(pd.read_csv(csv_file, encoding='utf-8', engine='python', error_bad_lines=False))
    df['created_at'] = df['created_at'].apply(lambda d: datetime.strptime(d, '%a %b %d %H:%M:%S %z %Y').strftime('%H:%M-%d-%m-%Y'))

    return df


def analyse_sentiment(data):

    """Given a Pandas dataframe with col 'text', this will apply the vaderSentiment dictionary
     in a new columns called 'vader_'"""

    #define the sentiment analyser object
    analyser = SentimentIntensityAnalyzer()

    #Initialise new column
    data['vader_neg'] = ""
    data['vader_neu'] = ""
    data['vader_pos'] = ""
    data['vader_comp'] = ""

    # Insert the vader scores
    for row in range(data.shape[0]):
        data.loc[[row], ['vader_neg']] = analyser.polarity_scores(data['text'][row])['neg']
        data.loc[[row], ['vader_neu']] = analyser.polarity_scores(data['text'][row])['neu']
        data.loc[[row], ['vader_pos']] = analyser.polarity_scores(data['text'][row])['pos']
        data.loc[[row], ['vader_comp']] = analyser.polarity_scores(data['text'][row])['compound']

    return data


if __name__ == "__main__":

    # check csv assigned
    if not (len(sys.argv) == 2):
        print(f"Please assign your CSV file.")
        sys.exit(0)

    # check that inputs exist.
    if not os.path.isfile(sys.argv[1]):
        print(f"The CSV file", sys.argv[1], "doesn't seem to exist.")
        sys.exit(0)

    # Put the csv file into a dataframe
    df = set_up_dataframe(csv_file = sys.argv[1])

    analyse_sentiment(df)

    df_cleaning_functions.vader_df_2_geojson(df)

    output_filename = os.path.splitext(sys.argv[1])[0] + '_VADER.csv'

    df.to_csv(output_filename, sep=',', encoding='utf-8')
    
