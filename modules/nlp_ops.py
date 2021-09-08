
#~ Standard library imports
import csv
import sys
import os
import re
from collections import namedtuple, Counter

#~ 3rd party imports
import pymongo
from alive_progress import alive_bar
import liwc
from textblob import TextBlob

#~ Local application imports
from modules import (
    mongo_ops,
    epicosm_meta,
    twitter_ops,
    nlp_ops,
    env_config,
    mongodb_config,
    vader_sentiment,
    labmt)


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

    #~ Turn csv into named tuple, for dot notation in pymongo ops
    with open("groundtruth.csv") as incoming_csv:

        reader = csv.reader(incoming_csv)
        Data = namedtuple("Data", next(reader))
        groundtruth_in = [Data(*r) for r in reader]

    #~ Count users in db and groundtruth for crosschecking
    total_users_in_db = mongodb_config.collection.distinct("user.id")
    users_with_groundtruth_provided = []

    #~ Create or update field (epicosm.groundtruth.gt_stat_1) with values
    for index, user in enumerate(groundtruth_in):

        mongodb_config.collection.update_many({"user.id": user.user},
                              {"$set":
                              {"epicosm.groundtruth.gt_stat_1": float(user.gt_stat_1)}})

        users_with_groundtruth_provided.append(user.user)

    print(f"OK - Groundtruth appended to {index + 1} users' records.")

    #~ Cross-checking of groundtruth against users in DB.
    existing_users_but_no_groundtruth = list(set(total_users_in_db) - set(users_with_groundtruth_provided))
    existing_groundtruths_but_no_user = list(set(users_with_groundtruth_provided) - set(total_users_in_db))

    #~ make some log files if there are discrepancies
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
    Apply VADER (Hutto & Gilbert 2014) analysis on the contents of the DB,
    appending four fields: epicosm.vader.negative epicosm.vader.neutral
    epicosm.vader.positive epicosm.vader.compound
    """

    print(f"Vader sentiment, analysing...")

    #~ initialise analyser
    analyser = vader_sentiment.SentimentIntensityAnalyzer()

    #~ analyse and insert each vader score for each tweet text
    with alive_bar(total_records, spinner="dots_recur") as bar:
        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            #~ get the text field for this record
            full_text_field = db_document_dict["text"]

            #~ vader process
            vader_negative = analyser.polarity_scores(full_text_field)["neg"]
            vader_neutral = analyser.polarity_scores(full_text_field)["neu"]
            vader_positive = analyser.polarity_scores(full_text_field)["pos"]
            vader_compound = analyser.polarity_scores(full_text_field)["compound"]

            mongodb_config.collection.update_one(
                {"id": db_document_dict["id"]},
                {"$set": {
                    "epicosm.vader.negative": vader_negative,
                    "epicosm.vader.neutral": vader_neutral,
                    "epicosm.vader.positive": vader_positive,
                    "epicosm.vader.compound": vader_compound}})

            bar()

    print(f"OK - Vader sentiment analysis applied to {index + 1} records.")


def mongo_labMT(db, total_records):

    """
    Apply labMT (Dodds & Danforth 2011) to contents of DB,
    appending one field to each record, called epicosm.labMT.emotion_valence
    """

    print(f"labMT sentiment, analysing...")

    lang = "english"
    labMT, labMTvector, labMTwordList = labmt.emotionFileReader(stopval=0.0, lang=lang, returnVector=True)

    with alive_bar(total_records, spinner="dots_recur") as bar:

        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            #~ get the text field for this record
            full_text_field = db_document_dict["text"]

            #~ compute valence score and return frequency vector for generating wordshift
            valence, frequency_vector = labmt.emotion(
                full_text_field,
                labMT,
                shift=True,
                happsList=labMTvector)

            #~ assign a stop vector
            stop_vector = labmt.stopper(
                frequency_vector,
                labMTvector,
                labMTwordList,
                stopVal=1.0)

            #~ get the emotional valence
            output_valence = labmt.emotionV(stop_vector, labMTvector)

            #~ insert score into DB
            mongodb_config.collection.update_one(
                {"id": db_document_dict["id"]},
                {"$set": {"epicosm.labMT.emotion_valence":
                float(format(output_valence, '.4f'))}})

            bar()

    print(f"OK - labMT sentiment analysis applied to {index + 1} records.")


def mongo_textblob(db, total_records):

    """
    Apply TextBlob to contents of DB,
    appending one field to each record, called epicosm.textblob
    """

    print(f"TextBlob sentiment, analysing...")

    with alive_bar(total_records, spinner="dots_recur") as bar:
        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            #~ get the text field for this record
            full_text_field = db_document_dict["text"]

            #~ we want textblob to ignore sentences and take tweets as a whole
            text_clean = full_text_field.replace(".", " ")

            blob = TextBlob(text_clean)
            blob.tags
            blob.noun_phrases

            for sentence in blob.sentences:
                mongodb_config.collection.update_one(
                    {"id": db_document_dict["id"]},
                    {"$set": {
                        "epicosm.textblob":
                        float(format(sentence.sentiment.polarity, '.4f'))}})

            bar()

    print(f"OK - TextBlob sentiment analysis applied to {index + 1} records.")


def mongo_liwc(db, total_records):

    """
    Do LIWC (Pennebaker et al 2015) to contents of DB,
    appending 78 (?) metric fields to DB.

    Requires an LIWC dictionary, named LIWC.dic, in the run folder.

    Appends fields epicosm.liwc.[category]
    """

    #~ Look for an LIWC dictionary
    if os.path.isfile('./LIWC.dic'):
        dictionary = "LIWC.dic"
    else:
        print(f"Please have your dictionary here, named LIWC.dic")
        return #~ abort LIWC if not dictionary

    def tokenize(text):

        """Split each text entry into words (tokens)"""

        for match in re.finditer(r"\w+", text, re.UNICODE):
            yield match.group(0)

    print(f"LIWC sentiment, analysing...")

    parse, category_names = liwc.load_token_parser(dictionary)

    with alive_bar(total_records, spinner="dots_recur") as bar:

        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            #~ get the text field for this record
            full_text_field = db_document_dict["text"]

            word_count = len(re.findall(r'\w+', full_text_field))
            text_tokens = tokenize(full_text_field)
            text_counts = Counter(category for token in text_tokens for category in parse(token))

            for count_category in text_counts:  #~ insert the LIWC values as proportion of word_count

                mongodb_config.collection.update_one(
                    {"id": db_document_dict["id"]},
                    {"$set": {
                        "epicosm.liwc." + count_category:
                        float(format((text_counts[count_category] / word_count), '.4f'))}})

            bar()

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

    with alive_bar(total_records, spinner="dots_recur") as bar:

        for index, db_document_dict in enumerate(mongodb_config.collection.find({})):

            #~ get the text field for this record
            full_text_field = db_document_dict["text"]

            count = Counter(full_text_field)
            mongodb_config.collection.update_one({
                "id": db_document_dict["id"]},
                {"$set": {
                    "epicosm.trivial_nlp.e_ratio":
                    float(format(int(count['e']) / int(len(full_text_field)), '.4f'))}})
            bar()

    print(f"OK - e_ratio analysis applied to {index + 1} records.")


def mongo_groundtruth_delta(db, candidate_inference):

    """
    This is a placeholder for ascertaining how well a candidate analysis
    algorithm is correlating with groundtruth
    """

    with alive_bar(total_records, spinner="dots_recur") as bar:

        for index, tweet_text in enumerate(mongodb_config.collection.find({}, {"id": 1, interest_field: 1})):

            groundtruth_delta = groundtruthfield - candidate_inference_output_field

            mongodb_config.collection.update_one({
                "id": tweet_text["id"]},
                {"$set": {
                    "epicosm." + candidate_inference + ".groundtruth_delta":
                    format(groundtruth_delta, '.4f')}})

        bar()

