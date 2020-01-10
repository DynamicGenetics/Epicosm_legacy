import pandas as pd
from pandas import DataFrame
import sys
import os
import liwc
import re
from collections import Counter
from datetime import datetime


# Set up the dataframe by importing tweet.csv and setting up columns
def set_up_dataframe(csv_file, category_names):

    """ Build a dataframe with a tweet for each row.

    Rows are tweets, columns are time tweeted to the day,
    and to keep consistency with LIWC official output
    we add append word count and categories (otherwise if it appends
    them later it can get messy"""

    # the read_csv engine must be python, not default of c, or some lines will mess with it
    df = DataFrame(pd.read_csv(csv_file, encoding='utf-8', engine='python', error_bad_lines=False))
    df['created_at'] = df['created_at'].apply(lambda d: datetime.strptime(d, '%a %b %d %H:%M:%S %z %Y').strftime('%d-%m-%Y'))
    df['word_count'] = 0     # addend wc (consistent with official liwc format output)
    for category in category_names:
        df[category] = 0.0   # append the category columns
    return df


def tokenize(text):

    """Split each text entry into words (tokens)"""

    for match in re.finditer(r'\w+', text, re.UNICODE):
        yield match.group(0)


def load_dictionary(dictionary):
    parse, category_names = liwc.load_token_parser(dictionary)
    return parse, category_names


def count_and_insert(df, parse_fn):

    """Assign each word to dictionary category and put in dataframe"""

    index = 0
    df['word_count'] = df['text'].apply(lambda x: len(str(x).split(' ')))
    for tweet in df['text']:
        text_tokens = tokenize(tweet)
        text_counts = Counter(category for token in text_tokens for category in parse_fn(token))
        for count_category in text_counts: # insert the LIWC values as proportion of word_count
            df.at[index, count_category] = text_counts[count_category] / (df.iloc[index]['word_count'])
        index += 1


def liwc_analysis(csv_file, category_names, parse):
    df = set_up_dataframe(csv_file=csv_file, category_names=category_names)
    count_and_insert(df, parse_fn=parse)
    df_anonymised = df.drop(['text'], axis=1)
    df_anonymised.to_csv(csv_file + 'LIWC', sep=',', encoding='utf-8')


def csv_2_liwc_run():
    # check that inputs exist.
    if len(sys.argv) != 3:
        print(f'Please assign your dictionary and file to analyse.')
        print(f'eg: python3 main.py LIWC.dic some.txt')
        exit(0)
    if not os.path.isfile(sys.argv[1]):
        print(f"The dictionary", sys.argv[1], "doesn't seem to exist.")
        exit(0)
    if not os.path.isfile(sys.argv[2]):
        print(f"The CSV file", sys.argv[2], "doesn't seem to exist.")
        exit(0)

    # bring the dictionary in, sys.argv[1] is the dictionary name
    print(f"Analysing", sys.argv[2], "using LIWC, just a moment...")
    parse, category_names = liwc.load_token_parser(sys.argv[1])
    df = set_up_dataframe(csv_file=sys.argv[2], category_names=category_names)
    count_and_insert(df, parse_fn=parse)
    df_anonymised = df.drop(['id_str', 'text', 'retweeted_status.full_text'], axis=1)
    output_filename = os.path.splitext(sys.argv[2])[0] + '_LIWC.csv'
    df_anonymised.to_csv(output_filename, sep=',', encoding='utf-8')


if __name__ == '__main__':

    csv_2_liwc_run()
    
