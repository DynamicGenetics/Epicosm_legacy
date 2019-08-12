#########################################################################################
## epicosm.py - Al Tanner, 2019 - a twitter havester using MongoDB for data management ##
#########################################################################################

import os
import sys
import time
import tweepy
import pymongo
import logging
import datetime
import subprocess
from zipfile import ZipFile

import credentials
from modules import mongo_ops, epicosm_status, twitter_ops

## set up a few run variables
start = time.time()
now = datetime.datetime.now()
client = pymongo.MongoClient('localhost', 27017)
db = client.twitter_db
collection = db.tweets
following_collection = db.following

## set up environment specific variables
if not os.path.exists('/.dockerenv'):   ## if not in docker container
    run_folder = os.getcwd() + '/'
    status_file = run_folder + 'STATUS'
    db_log_filename = '/'.join([run_folder, 'db_logs', now.strftime('%H:%M:%S_%d-%m-%Y') + '.log'])
    db_path = run_folder + '/db'
    csv_filename = run_folder + '/output/csv/' + now.strftime('%H:%M:%S_%d-%m-%Y') + '.csv'
    epicosm_log_filename = '/'.join([run_folder, 'epicosm_logs', now.strftime('%H:%M:%S_%d-%m-%Y') + '.log'])
    database_dump_path = run_folder + '/output'
else:                               ## if IS in docker container
    run_folder = '/root/host_interface/'
    status_file = '/root/host_interface/STATUS'
    db_log_filename = '/root/host_interface/db_logs/' + now.strftime('%H:%M:%S_%d-%m-%Y') + '.log'
    db_path = '/root/host_interface/db'
    epicosm_log_filename = '/root/host_interface/epicosm_logs/' + now.strftime('%H:%M:%S_%d-%m-%Y') + '.log'
    csv_filename = '/root/host_interface/output/csv/' + now.strftime('%H:%M:%S_%d-%m-%Y') + '.csv'
    database_dump_path = '/root/host_interface/output'

## check if MongoDB is present and correct
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

## Check user list exists and get it
if not os.path.exists(run_folder + 'user_list'):
    print(f"USAGE: please provide a list of users to follow, named 'user_list'.")
    sys.exit()
number_of_users_provided = sum(1 for line_exists in open(run_folder + 'user_list') if line_exists)
screen_names = list(dict.fromkeys(line.strip() for line in open(run_folder + 'user_list'))) # remove duplicates
screen_names = [name for name in screen_names if name] # remove empty lines

## Check or make directory structure
if not os.path.exists(run_folder + '/db'):
    print(f"MongoDB database folder seems absent, creating folder...")
    os.makedirs(run_folder + '/db')
if not os.path.exists(run_folder + '/db_logs'):
    print(f"DB log folder seems absent, creating folder...")
    os.makedirs(run_folder + '/db_logs')
if not os.path.exists(run_folder + '/epicosm_logs'):
    print(f"Epicosm log folder seems absent, creating folder...")
    os.makedirs(run_folder + '/epicosm_logs')

## Set up logging
class StreamToLogger(object):
    """
    Write chatter to logfile.
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

if '--log' in sys.argv: # if --log given as argument, create a logfile for this run 
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
        filename = epicosm_log_filename,
        filemode='a'
    )
    stdout_logger = logging.getLogger('STDOUT')
    sl = StreamToLogger(stdout_logger, logging.INFO)
    sys.stdout = sl

    stderr_logger = logging.getLogger('STDERR')
    sl = StreamToLogger(stderr_logger, logging.ERROR)
    sys.stderr = sl

## connect to Twitter API
auth = tweepy.OAuthHandler(credentials.CONSUMER_KEY, credentials.CONSUMER_SECRET)
auth.set_access_token(credentials.ACCESS_TOKEN, credentials.ACCESS_TOKEN_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, retry_count=5, retry_delay=5, timeout=15)
try:
    print(f"Verifying Twitter credentials...")
    api.verify_credentials(retry_count=3, retry_delay=5)
except tweepy.error.TweepError:
    print(f"The API credentials do not seem valid: connection to Twitter refused.")
    sys.exit()


############
## run it ##
############

if __name__ == '__main__':

    try:
        ## check/start mongodb
        mongo_ops.start_mongo(mongod_executable_path,
                              db_path, 
                              db_log_filename)
        ## modify status file
        epicosm_status.status_up(collection,
                                 status_file)
        ## tidy up the database for better efficiency
        mongo_ops.index_mongo(run_folder,
                              db)
        ## get persistent user ids from screen names
        twitter_ops.lookup_users(run_folder,
                                 screen_names,
                                 api)
        ## get tweets for each user and archive in mongodb
        twitter_ops.harvest(run_folder,
                            db,
                            api,
                            collection)
        ## create CSV ouput and backup mongodb
        mongo_ops.export_and_backup(mongoexport_executable_path,
                                    mongodump_executable_path,
                                    database_dump_path,
                                    csv_filename)
        ## modify status file
        epicosm_status.status_down(collection,
                                   status_file,
                                   run_folder)
        ## shut down mongodb
        mongo_ops.stop_mongo(client)

        print(f"\nAll done, Epicosm finished at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}, taking around {int(round((time.time() - start) / 60))} minutes.")

    except KeyboardInterrupt:
        print(f"\n\nCtrl-c, ok got it, just a second while I try to exit gracefully...")
        with open(status_file, 'w+') as status:
            status.write(f"Epicosm is currently idle, but was interruped by user on last run.\nThe most recent harvest was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\n")
        stop_mongo(client)
        sys.exit()

