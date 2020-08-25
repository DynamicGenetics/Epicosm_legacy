import datetime
import os
import pymongo
import sys
import logging
import subprocess

# local imports
from modules import env_config, mongo_ops


env = env_config.EnvironmentConfig()
client = pymongo.MongoClient('localhost', 27017)
db = client.twitter_db
collection = db.tweets


# Catch ctrl-c signals (and kill -15 signals)
def signal_handler(sig, frame):

    """Handle interrupt signals, eg ctrl-c (and other kill signals).

    Exiting more abruptly can leave MongoDB running, which can cause issues,
    so Mongo is asked to stop
    """
    status_file = env.status_file
    print(f"Just a second while I try to exit gracefully...")
    mongo_ops.stop_mongo(env.db_path)
    sys.exit()


# Check if this is being run as native or compiled python
def native_or_compiled():

    run_method = "native python"

    if getattr(sys, "frozen", False):
        # we are running in a bundle
        run_method = "compiled python"
        bundle_dir = sys._MEIPASS

    else:
        # we are running native python
        bundle_dir = os.path.dirname(os.path.abspath(__file__))

    print("Epicosm launching as", run_method)

    return bundle_dir


def logger_setup(epicosm_log_filename):

    """ General logging of print statements"""

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

    print("Epicosm running, the logfile for this run is:\n", epicosm_log_filename)
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
                        filename = epicosm_log_filename,
                        filemode='a')
    stdout_logger = logging.getLogger('STDOUT')
    sl = StreamToLogger(stdout_logger, logging.INFO)
    sys.stdout = sl
    stderr_logger = logging.getLogger('STDERR')
    sl = StreamToLogger(stderr_logger, logging.ERROR)
    sys.stderr = sl


def status_up(status_file):
    
    """ Update STATUS file in run folder to notify when running.
    
    Does a quick count of the current database,
    and rewrite the STATUS file to say that process is in progress."""
    
    tweet_count = collection.count_documents({})
    with open(status_file, 'w+') as status:
        status.write(f"Epicosm is currently running.\nThis process started at {datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}\n")
        if tweet_count > 0:
            status.write(f"The database currently contains {tweet_count} tweets.\n")


def status_down(status_file, run_folder):

    """ Update STATUS file in run folder to notify when idle, and next run.
                     
    Does a quick count of the current database,
    and rewrite the STATUS file to say that process is in progress."""

    tweet_count = collection.count_documents({})
    with open(status_file, 'w+') as status:
        next_harvest = (datetime.datetime.now() + datetime.timedelta(hours = 72)).strftime('%Y-%m-%d_' + "06:00:00")
        status.write(f"Epicosm is currently idle.\nThe most recent harvest was at {datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}\nThe database currently contains {tweet_count} tweets.\n")


def check_env():
    # check if MongoDB is present and correct
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

    # Check user list exists and get it
    if not os.path.exists(env.run_folder + '/user_list'):
        print(f"USAGE: please provide a list of users to follow, named 'user_list'. Stopping.")
        sys.exit()

    # Check credentials is present and correct
    credentials = {}
    try:
        with open("credentials.txt") as file:
            for line in file:
                line = line.strip()  # remove errant whitespace
                if line and not line.startswith("#"): # take the non-commented lines
                    try:
                        key, val = line.split()
                        if val:
                            credentials[key.upper()] = val
                    except ValueError: # users might have forgotten to update the credentials template file
                        print("Your credentials.txt file doesn't look complete.")
                        sys.exit()
    except FileNotFoundError:
        print("Your credentials.txt file doesn't seem to exist here.")
        sys.exit()

    number_of_users_provided = sum(1 for line_exists in open(env.run_folder + '/user_list') if line_exists)
    screen_names = list(dict.fromkeys(line.strip() for line in open(env.run_folder + '/user_list'))) # remove duplicates
    screen_names = [name for name in screen_names if name] # remove empty lines

    # Check or make directory structure
    if not os.path.exists(env.run_folder + '/db'):
        print(f"Looks like your first run here: making folders.")
        os.makedirs(env.run_folder + '/db')
    if not os.path.exists(env.run_folder + '/db_logs'):
        os.makedirs(env.run_folder + '/db_logs')
    if not os.path.exists(env.run_folder + '/epicosm_logs'):
        os.makedirs(env.run_folder + '/epicosm_logs')

    return mongod_executable_path, mongoexport_executable_path, mongodump_executable_path, screen_names
