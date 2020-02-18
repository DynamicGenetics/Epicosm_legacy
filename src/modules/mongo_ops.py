import os
import subprocess
import sys
import time
import psutil
import pymongo


def mongo_checks():

    """figure out where mongodb executables are on this system,
    assign them to variables"""

    try:
        mongod_executable_path = subprocess.check_output(['which', 'mongod']).decode('utf-8').strip()
    except:
        print(f"You don't seem to have MongoDB installed. Stopping.")
        sys.exit()
    try:
        mongoexport_executable_path = subprocess.check_output(['which', 'mongoexport']).decode('utf-8').strip()
    except:
        print(f"Mongoexport seems missing... stopping.")
        sys.exit()
    try:
        mongodump_executable_path = subprocess.check_output(['which', 'mongodump']).decode('utf-8').strip()
    except:
        print(f"Mongodump seems missing... stopping.")
        sys.exit()
    try:
        mongoimport_executable_path = subprocess.check_output(['which', 'mongoimport']).decode('utf-8').strip()
    except:
        print(f"Mongoimport seems missing... stopping.")
        sys.exit()

    return mongod_executable_path, mongoexport_executable_path, mongodump_executable_path, mongoimport_executable_path


def start_mongo(mongod_executable_path, db_path, db_log_filename):

    """Spin up a MongoDB daemon (mongod) from the shell.
    
    The db path is set as suitable to the environment (locally in the 
    folder it is run in, but docker in the volumes folder).
    pgrep will look for running mongod processes and inform of conflicts,
    but this might throw an error if it comes across a zombie, in which case
    it ignores it and carries on with starting the daemon."""

    def mongo_go():
        print(f"\nStarting the MongoDB daemon...\n")
        try:
            subprocess.Popen([mongod_executable_path, '--dbpath', db_path, '--logpath', db_log_filename], stdout=subprocess.DEVNULL)
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            print(f"There is a problem opening the MonogoDB daemon... halting.\n", e.output)
            sys.exit()

    try:
        if 'mongod' in (p.name() for p in psutil.process_iter()):
            print(f"\nMongoDB daemon appears to be already running. This could cause conflicts. Please stop the daemon and retry.")
            print(f"(You can do this with the command: pkill -15 mongod)\n")
            sys.exit()
        else:
            mongo_go()
    except psutil.ZombieProcess:
        mongo_go()


def stop_mongo():

    """ Gracefully close the mongo daemon.
    
    pkill -15 is a standard way of ending mongod, which will close connections
    cleanly. """

    client = pymongo.MongoClient('localhost', 27017)
    print(f"\nAsking MongoDB to close...")
    client.close()
    subprocess.call(['pkill', '-15', 'mongod'])
    timeout = 60
    while timeout > 0: # wait one minute for mongod to close
        try:
            subprocess.check_output(['pgrep', 'mongod'])
        except subprocess.CalledProcessError:
            print(f"\nOK, MongoDB daemon closed.")
            break
        print(".", end='', flush=True)
        time.sleep(1)
        timeout -= 1
    if timeout == 0: # this has never happened...
        print(f"\nMongoDB didn't respond to requests to close... be aware that MongoDB is still running.")


def index_mongo(run_folder):

    """Tidy up the database so that upsert operations are faster."""

    client = pymongo.MongoClient('localhost', 27017)
    db = client.twitter_db
    if not os.path.isfile(run_folder + '/db/WiredTiger'):
        return
    print(f"Indexing MongoDB...")
    db.tweets.create_index([('id_str', pymongo.ASCENDING)], unique=True, dropDups=True)


def export_csv(mongoexport_executable_path, csv_filename):

    """Export some fields from the tweets in MongoDB into a CSV file."""

    # export selected fields (specified after --fields) into csv
    print(f"\nCreating CSV output file...")
    subprocess.call([mongoexport_executable_path, '--host=127.0.0.1', '--db', 'twitter_db', '--collection', 'tweets', '--type=csv', '--out', csv_filename, '--fields', 'user.id_str,id_str,created_at,full_text,retweeted_status.full_text'], stderr=subprocess.DEVNULL)


def export_json(mongoexport_executable_path, json_filename):

    """Export ALL fields (json export cannot currently specify fields) into JSON file
    THIS WILL BE A LARGE FILE, AND TAKE A LONG TIME IF THE DB IS LARGE!!!"""

    print(f"\nCreating JSON output file...")
    subprocess.call([mongoexport_executable_path, '--host=127.0.0.1', '--db', 'twitter_db', '--collection', 'tweets', '--type=json', '--pretty', '--out', json_filename], stderr=subprocess.DEVNULL)


def backup_db(mongodump_executable_path, database_dump_path):
    
    """ Do a full backup of the database into BSON format """
    
    print(f'\nBacking up the database...')
    subprocess.call([mongodump_executable_path, '-o', database_dump_path, '--host=127.0.0.1'], stderr=subprocess.DEVNULL)
    subprocess.call(['chmod', '-R', '0755', database_dump_path]) # hand back permissions to host


def export_latest_tweet(mongoexport_executable_path):

    """Export most recent tweet as csv"""

    print(f"\nCreating CSV output file...")
    subprocess.call(
        [mongoexport_executable_path, '--host=127.0.0.1', '--db=geotweets', '--collection=geotweets_collection',
         '--type=csv', '--out=latest_geotweet.csv', '--fields=created_at,geo.coordinates,text', '--sort="{_id:-1}"',
         '--limit=1'])


def import_analysed_tweet(mongoimport_executable_path, latest_tweet):

    """Import metrics from sentiment analysis into MongoDB"""

    print(f"\nImporting LIWC analysis output...")
    subprocess.call(
        [mongoimport_executable_path, '--host=127.0.0.1', '--db=geotweets', '--collection=geotweets_analysed',
         '--type=csv', '--headerline', '--file=' + latest_tweet])
