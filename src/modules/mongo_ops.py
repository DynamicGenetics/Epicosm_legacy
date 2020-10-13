import os
import subprocess
import sys
import time
import psutil
import pymongo

#import mongodb_config
client = pymongo.MongoClient("localhost", 27017)
db = client.twitter_db
collection = db.tweets

def mongo_checks():

    """figure out where mongodb executables are on this system,
    assign them to variables"""

    try:
        mongod_executable_path = subprocess.check_output(["which", "mongod"]).decode("utf-8").strip()
    except:
        print(f"You don't seem to have MongoDB installed. Stopping.")
        sys.exit()
    try:
        mongoexport_executable_path = subprocess.check_output(["which", "mongoexport"]).decode("utf-8").strip()
    except:
        print(f"Mongoexport seems missing... stopping.")
        sys.exit()
    try:
        mongodump_executable_path = subprocess.check_output(["which", "mongodump"]).decode("utf-8").strip()
    except:
        print(f"Mongodump seems missing... stopping.")
        sys.exit()
    try:
        mongoimport_executable_path = subprocess.check_output(["which", "mongoimport"]).decode("utf-8").strip()
    except:
        print(f"Mongoimport seems missing... stopping.")
        sys.exit()

    return mongod_executable_path, mongoexport_executable_path, mongodump_executable_path, mongoimport_executable_path


def start_mongo(mongod_executable_path, db_path, db_log_filename, epicosm_log_filename):

    """Spin up a MongoDB daemon (mongod) from the shell.

    The db path is set as suitable to the environment (locally in the
    folder it is run in, but docker in the volumes folder).
    pgrep will look for running mongod processes and inform of conflicts,
    but this might throw an error if it comes across a zombie, in which case
    it ignores it and carries on with starting the daemon."""


    print(f"Starting the MongoDB daemon...")
    try:
        subprocess.Popen([mongod_executable_path, "--dbpath",
                          db_path, "--logpath", db_log_filename],
                          stdout = open(epicosm_log_filename, "a+"))
        time.sleep(1)
    except subprocess.CalledProcessError as e:
        print(f"Problem starting MongoDB:", e.output)
        sys.exit()


def stop_mongo(dbpath):

    """ Gracefully close the mongo daemon.
    
    pkill -15 is a standard way of ending mongod, which will close connections
    cleanly. """

    print(f"Asking MongoDB to close...")
    client.close()
    subprocess.call(["pkill", "-15", "mongod"])

    timeout = 60
    while timeout > 0: # wait one minute for mongod to close
        try:
            subprocess.check_output(["pgrep", "mongod"])
        except subprocess.CalledProcessError:
            print(f"OK, MongoDB daemon closed.")
            break
        time.sleep(1)
        timeout -= 1
    if timeout == 0: # wait 1 minutes, then let it go...
        print(f"MongoDB didn't respond to requests to close... be aware that MongoDB is still running.")
    return

def index_mongo(run_folder):

    """Tidy up the database so that upsert operations are faster."""

    if not os.path.isfile(run_folder + "/db/WiredTiger"):
        return
    print(f"Indexing MongoDB...")
    db.tweets.create_index([("id_str", pymongo.ASCENDING)],
                           unique=True, dropDups=True)


def export_csv_tweets(mongoexport_executable_path,
                      csv_tweets_filename,
                      epicosm_log_filename):

    """Export some fields from the tweets in MongoDB into a CSV file."""

    # export selected fields (specified after --fields) into csv
    print(f"Creating CSV output file...")
    subprocess.call([mongoexport_executable_path, "--host=127.0.0.1",
                     "--db", "twitter_db",
                     "--collection", "tweets",
                     "--type=csv",
                     "--out", csv_tweets_filename,
                     "--fields", "user.id_str,id_str,created_at,full_text,retweeted_status.full_text"],
                     stdout = open(epicosm_log_filename, "a+"),
                     stderr = open(epicosm_log_filename, "a+"))


def export_csv_friends(mongoexport_executable_path,
                       csv_friends_filename,
                       epicosm_log_filename):

    """Export all friends of users MongoDB into a CSV file."""

    # export selected fields (specified after --fields) into csv
    print(f"Creating CSV output file...")
    subprocess.call([mongoexport_executable_path, "--host=127.0.0.1",
                     "--db", "twitter_db",
                     "--collection", "friends",
                     "--type=csv",
                     "--out", csv_friends_filename,
                     "--fields", "user_id,friends"],
                     stdout = open(epicosm_log_filename, "a+"),
                     stderr = open(epicosm_log_filename, "a+"))


def backup_db(mongodump_executable_path, database_dump_path, epicosm_log_filename, processtime):
    
    """ Do a full backup of the database into BSON format """
    
    print(f"Backing up the database...")
    subprocess.call([mongodump_executable_path, "-o",
                     database_dump_path, "--host=127.0.0.1"],
                     stdout = open(epicosm_log_filename, "a+"),
                     stderr = open(epicosm_log_filename, "a+"))
    # mongodb doesn't give a naming option(?), so rename with the timestamp
    subprocess.call(["mv", database_dump_path + "/twitter_db/tweets.bson",
                     database_dump_path + "/twitter_db/tweets" + processtime + ".bson"])
    subprocess.call(["mv", database_dump_path + "/twitter_db/tweets.metadata.json",
                     database_dump_path + "/twitter_db/tweets" + processtime + ".metadata.json"])


def export_latest_tweet(mongoexport_executable_path, epicosm_log_filename):

    """Export most recent tweet as csv"""

    print(f"Creating CSV output file...")
    subprocess.call([mongoexport_executable_path, "--host=127.0.0.1",
                    "--db=geotweets", "--collection=geotweets_collection",
                    "--type=csv", "--out=latest_geotweet.csv",
                    "--fields=created_at,geo.coordinates,text",
                    '--sort="{_id:-1}"', "--limit=1"],
                    stdout = open(epicosm_log_filename, "a+"))


def import_analysed_tweet(mongoimport_executable_path, latest_tweet, epicosm_log_filename):

    """Import metrics from sentiment analysis into MongoDB"""

    print(f"Importing LIWC analysis output...")
    subprocess.call([mongoimport_executable_path, "--host=127.0.0.1",
                    "--db=geotweets", "--collection=geotweets_analysed",
                    "--type=csv", "--headerline", "--file=" + latest_tweet],
                    stdout = open(epicosm_log_filename, "a+"))

