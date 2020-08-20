import pymongo
import csv
import sys
from collections import namedtuple, Counter
from tqdm import tqdm
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from labMTsimple.storyLab import *
import liwc
from textblob import TextBlob


from modules import mongo_ops, epicosm_meta, twitter_ops, nlp_ops, env_config, mongodb_config

def tweet_or_retweet(db_document_dict):

    """
    tweet jsons are kind of moronic - if the tweet is a retweet, the full_text field is
    truncated (ending with single character ellipsis (...)),
    and the field underneath called 'truncated' says 'false'.
    I do not know when the 'truncated' field does not say false.

    Anyway, we have to get the *true* full text from the field retweeted_status.full_text
    in the case that a tweet is a retweet -.-

    tweet_text is a dict created by the pymongo query like
    db[collection_name].find({}, {"id_str": 1, "full_text": 1, "retweeted_status.full_text": 1})
    """

    full_text_field = "db_document_dict[\"full_text\"]"

    if "retweeted_status" in db_document_dict:  # if this key exists, it is a retweet
        full_text_field = "db_document_dict[\"retweeted_status\"][\"full_text\"]"

    return full_text_field


def mongo_insert_groundtruth(db, total_records):

    """
    Open up the local MongoDB, and for each record
    insert values representing groundtruth.
    These go in new fields, or if the fields already exist
    they are updated.

    The groundtruth.csv must be in csv format, with two fields
    user_id and a float. user_id is the twitter id number,
    and the float for the ground truth is a random number -1 < x < 1
    """

    print(f"Inserting groundtruth values...")

    # Turn csv into named tuple, for dot notation in pymongo ops
    with open("groundtruth.csv") as incoming_csv:

        reader = csv.reader(incoming_csv)
        Data = namedtuple("Data", next(reader))
        groundtruth_in = [Data(*r) for r in reader]

    # Count users in db and groundtruth for crosschecking
    total_users_in_db = mongodb_config.collection.distinct("user.id_str")
    users_with_groundtruth_provided = []

    # Create or update field (epicosm.groundtruth.gt_stat_1) with values
    for index, user in enumerate(groundtruth_in):

        mongodb_config.collection.update_many({"user.id_str": user.user},
                              {"$set":
                              {"epicosm.groundtruth.gt_stat_1": float(user.gt_stat_1)}})

        users_with_groundtruth_provided.append(user.user)

    print(f"OK - Groundtruth appended to {index + 1} users' records.")

    # Cross-checking of groundtruth against users in DB.
    existing_users_but_no_groundtruth = list(set(total_users_in_db) - set(users_with_groundtruth_provided))
    existing_groundtruths_but_no_user = list(set(users_with_groundtruth_provided) - set(total_users_in_db))

    # make some log files if there are discrepancies
    if len(existing_groundtruths_but_no_user) > 0:

        print("Groundtruth was provided for", len(existing_groundtruths_but_no_user), "users not appearing in the DB.",
              "See groundtruth_but_no_user.log")

        with open("groundtruth_but_no_user.log", "w") as save_file:
            for user in existing_groundtruths_but_no_user:
                save_file.write("%s\n" % user)

    if len(existing_users_but_no_groundtruth) > 0:

        print("Groundtruth was not provided for", len(existing_users_but_no_groundtruth), "users appearing in the DB.",
              "See user_but_no_groundtruth.log")

        with open("user_but_no_groundtruth.log", "w") as save_file:
            for user in existing_users_but_no_groundtruth:
                save_file.write("%s\n" % user)


def mongo_vader(db, total_records):

    """
    Do Vader (Hutto & Gilbert 2014) analysis on the contents of the DB,
    appending four fields: epicosm.vader.negative epicosm.vader.neutral
    epicosm.vader.positive epicosm.vader.compound
    """

    print(f"Vader sentiment, analysing...")

    # initialise analyser
    analyser = SentimentIntensityAnalyzer()

    # analyse and insert each vader score for each tweet text
    with tqdm(total=total_records, file=sys.stdout) as pbar:

        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            # decide if it is a tweet or retweet and assign relevant field
            full_text_field = eval(tweet_or_retweet(db_document_dict))

            vader_negative = analyser.polarity_scores(full_text_field)["neg"]
            vader_neutral = analyser.polarity_scores(full_text_field)["neu"]
            vader_positive = analyser.polarity_scores(full_text_field)["pos"]
            vader_compound = analyser.polarity_scores(full_text_field)["compound"]

            mongodb_config.collection.update_one({"id_str": db_document_dict["id_str"]}, {"$set": {
                                  "epicosm.vader.negative": vader_negative,
                                  "epicosm.vader.neutral": vader_neutral,
                                  "epicosm.vader.positive": vader_positive,
                                  "epicosm.vader.compound": vader_compound}})

            pbar.update(1)

    print(f"OK - Vader sentiment analysis applied to {index + 1} records.")


def mongo_labMT(db, total_records):

    """
    Do labMT (Dodds & Danforth 2011) to contents of DB,
    appending one field called epicosm.labMT.emotion_valence
    """

    print(f"labMT sentiment, analysing...")

    lang = 'english'
    labMT, labMTvector, labMTwordList = emotionFileReader(stopval=0.0, lang=lang, returnVector=True)

    with tqdm(total=total_records, file=sys.stdout) as pbar:

        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            # decide if it is a tweet or retweet and assign relevant field
            full_text_field = eval(tweet_or_retweet(db_document_dict))

            # compute valence score and return frequency vector for generating wordshift
            valence, frequency_vector = emotion(full_text_field, labMT, shift=True, happsList=labMTvector)

            # assign a stop vector
            stop_vector = stopper(frequency_vector, labMTvector, labMTwordList, stopVal=1.0)

            # get the emotional valence
            output_valence = emotionV(stop_vector, labMTvector)

            # insert score into DB
            mongodb_config.collection.update_one({"id_str": db_document_dict["id_str"]}, {"$set": {
                                  "epicosm.labMT.emotion_valence": float(format(output_valence, '.4f'))}})

            pbar.update(1)

    print(f"OK - labMT sentiment analysis applied to {index + 1} records.")


def mongo_textblob(db, total_records):

    print(f"TextBlob sentiment, analysing...")

    with tqdm(total=total_records, file=sys.stdout) as pbar:

        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            # decide if it is a tweet or retweet and assign relevant field
            full_text_field = eval(tweet_or_retweet(db_document_dict))

            # we want textblob to ignore sentences and take tweets as a whole
            text_clean = full_text_field.replace(".", " ")

            blob = TextBlob(text_clean)
            blob.tags
            blob.noun_phrases

            for sentence in blob.sentences:
                mongodb_config.collection.update_one({"id_str": db_document_dict["id_str"]},
                                                     {"$set": {"epicosm.textblob":
                                                      float(format(sentence.sentiment.polarity, '.4f'))}})
            pbar.update(1)

    print(f"OK - TextBlob sentiment analysis applied to {index + 1} records.")


def mongo_liwc(db, total_records):

    """
    Do LIWC (Pennebaker et al 2015) to contents of DB,
    appending 78 (?) metric fields to DB.

    Requires an LIWC dictionary, named LIWC.dic, in the run folder.

    Appends fields epicosm.liwc.[category]
    """

    def tokenize(text):

        """Split each text entry into words (tokens)"""

        for match in re.finditer(r'\w+', text, re.UNICODE):
            yield match.group(0)

    # Look for an LIWC dictionary
    if os.path.isfile('./LIWC.dic'):
        dictionary = "LIWC.dic"
    else:
        print(f"Please have your dictionary here, named LIWC.dic")
        return  # abort LIWC if not dictionary

    print(f"LIWC sentiment, analysing...")

    parse, category_names = liwc.load_token_parser(dictionary)

    with tqdm(total=total_records, file=sys.stdout) as pbar:

        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            # decide if it is a tweet or retweet and assign relevant field
            full_text_field = eval(tweet_or_retweet(db_document_dict))

            word_count = len(re.findall(r'\w+', full_text_field))
            text_tokens = tokenize(full_text_field)
            text_counts = Counter(category for token in text_tokens for category in parse(token))

            for count_category in text_counts:  # insert the LIWC values as proportion of word_count

                mongodb_config.collection.update_one({"id_str": db_document_dict["id_str"]},
                                               {"$set":
                                               {"epicosm.liwc." + count_category:
                                               float(format((text_counts[count_category] / word_count),
                                               '.4f'))}})

            pbar.update(1)

    print(f"OK - LIWC sentiment analysis applied to {index + 1} records.")


def mongo_time_of_day(db, total_records):

    """Apply a fuzzy time of day field eg early morning/midday/evening etc"""

    pass


def mongo_extract_emojis(db, total_records):

    """Find emojis used in the post and copy them to an epicosm subfield."""

    pass


def mongo_nlp_example(db, total_records):

    """
    This is a trivial placeholder for custom analyses.
    Outputs the ratio of the letter 'e' to total characters
    in field epicosm.trivial_nlp.e_ratio
    """

    print(f"e_ratio, analysing...")

    with tqdm(total=total_records, file=sys.stdout) as pbar:

        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            # decide if it is a tweet or retweet and use correct field
            full_text_field = eval(tweet_or_retweet(db_document_dict))

            count = Counter(full_text_field)
            mongodb_config.collection.update_one({"id_str": db_document_dict["id_str"]},
                                           {"$set":
                                           { "epicosm.trivial_nlp.e_ratio":
                                           float(format(int(count['e']) / int(len(full_text_field)), '.4f'))}})

            pbar.update(1)

    print(f"OK - e_ratio analysis applied to {index + 1} records.")


def mongo_groundtruth_delta(db, candidate_inference):

     """
     This is a placeholder for ascertaining how well a candidate analysis
     algorithm is correlating with groundtruth
     """

     with tqdm(total=total_records, file=sys.stdout) as pbar:

         for index, tweet_text in enumerate(mongodb_config.collection.find({}, {"id_str": 1, interest_field: 1})):

             groundtruth_delta = groundtruthfield - candidate_inference_output_field

             mongodb_config.collection.update_one({"id_str": tweet_text["id_str"]}, {"$set": {
                 "epicosm." + candidate_inference + ".groundtruth_delta": format(groundtruth_delta, '.4f')}})

         pbar.update(1)

