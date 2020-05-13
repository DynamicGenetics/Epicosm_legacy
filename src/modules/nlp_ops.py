import pymongo
import csv
from collections import namedtuple

# Local imports
import mongo_ops

# this'll be where nlp modules go

def insert_groundtruth():

    """ Open up the local MongoDB, and for each record
    insert values representing groundtruth.
    These go in new fields, or if the fields already exist
    they are updated.

    The gt_input_file must be in csv format, with two fields
    user_id and a float. in this prototype, user_id is the twitter id,
    and the float for the ground truth is a random number -1 < x < 1"""

    client = pymongo.MongoClient('localhost', 27017)
    db = client.twitter_db # how can we fix this? repetitive.

    # Turn csv into named tuple, for easier dot notation in pymongo ops
    with open("groundtruth.csv") as incoming_csv:

        reader = csv.reader(incoming_csv)
        Data = namedtuple("Data", next(reader))
        groundtruth_in = [Data(*r) for r in reader]

    # Create or update fields (epicosm.grountruth_1) with values
    for user in groundtruth_in:

        db.tweets.update_many({"user.id_str": user.user}, {"$set": {"epicosm.groundtruth_1": user.gt_stat_1}})

#debug
insert_groundtruth()


def mongo_vader(dbpath, db, collection):
    pass
    # make new fields in mongodb

def mongo_liwc(dbpath, db, collection):
    pass

def mongo_labmt(dbpath, db, collection):
    pass

def custom_nlp(dpbath, db, collection, nlp_name):
    pass
    # make a df of tweets (which fields?)

    # add fields for nlp output

    # do nlp and fill fields

    # reinsert back to db
