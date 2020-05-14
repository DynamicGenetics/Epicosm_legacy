import pymongo
import csv
from collections import namedtuple
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Link up the local DB
client = pymongo.MongoClient('localhost', 27017)
db = client.twitter_db

def insert_groundtruth(db):

    """ Open up the local MongoDB, and for each record
    insert values representing groundtruth.
    These go in new fields, or if the fields already exist
    they are updated.

    The gt_input_file must be in csv format, with two fields
    user_id and a float. in this prototype, user_id is the twitter id,
    and the float for the ground truth is a random number -1 < x < 1"""

    print(f"Inserting groundtruth values...")

    # Turn csv into named tuple, for easier dot notation in pymongo ops
    with open("groundtruth.csv") as incoming_csv:

        reader = csv.reader(incoming_csv)
        Data = namedtuple("Data", next(reader))
        groundtruth_in = [Data(*r) for r in reader]

    # Create or update fields (epicosm.grountruth_1) with values
    for index, user in enumerate(groundtruth_in):

        db.tweets.update_many({"user.id_str": user.user}, {"$set": {"epicosm.groundtruth.gt_stat_1": user.gt_stat_1}})

    # Need "this user is not in the database"

    print(f"OK - Groundtruth appended to {index + 1} users' records.")

#debug
insert_groundtruth(db)


def mongo_vader(db):

    """Do Vader (Hutto & Gilbert 2014) analysis on the contents of the DB,
    appending positive, negative, neutral and compound metrics to DB."""

    print(f"Vader sentiment, analysing...")

    # initialise analyser
    analyser = SentimentIntensityAnalyzer()

    # analyse and insert each vader score for each tweet text
    for index, tweet_text in enumerate(db.tweets.find({}, {"id_str": 1, "full_text": 1})):

        vader_negative = analyser.polarity_scores(tweet_text["full_text"])['neg']
        vader_neutral = analyser.polarity_scores(tweet_text["full_text"])['neu']
        vader_positive = analyser.polarity_scores(tweet_text["full_text"])['pos']
        vader_compound = analyser.polarity_scores(tweet_text["full_text"])['compound']

        db.tweets.update_one({"id_str": tweet_text["id_str"]}, {"$set": {
                              "epicosm.vader.neg": vader_negative,
                              "epicosm.vader.neu": vader_neutral,
                              "epicosm.vader.pos": vader_positive,
                              "epicosm.vader.comp": vader_compound}})

    print(f"OK - Vader sentiment analysis applied to {index + 1} records.")

#debug
mongo_vader(db)


def mongo_labmt(dbpath, db, collection):

    """Do LabMT (Dodds & Danforth XXXX) to contents of DB,
    appending positive and negative metric fields to DB."""

    print(f"LabMT sentiment, analysing...")

    pass



def mongo_liwc(dbpath, db, collection):

    """Do LIWC (Pennebaker et al 2015) to contents of DB,
    appending 78 (?) metric fields to DB.

    Requires an LIWC dictionary, named LIWC.dic, in the run folder."""

    print(f"LIWC sentiment, analysing...")

    pass


def mongo_time_of_day(db):

    """Apply a fuzzy time of day field eg early morning/midday/evening etc"""

    pass


def mongo_extract_emojis(db):

    """Find emojis used in the post and copy them to an epicosm subfield."""

    pass


def mongo_groundtruth_deltas(db):
    # give a metric of difference from groundtruth of candidate senti-analysis
    # root mean squares?
    pass


def custom_senti_analysis(dpbath, db, collection, nlp_name):
    pass
    # make a df of tweets (which fields?)

    # add fields for nlp output

    # do nlp and fill fields

    # reinsert back to db
