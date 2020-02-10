# -*- coding: utf-8 -*-

import os
import sys
import time
import datetime
import subprocess
import signal

# local imports 
try:
    import credentials
except:
    print(f"Your credentials.py file doesn't seem to be here... stopping.")
    sys.exit(0)

# from ./modules
from modules import mongo_ops, epicosm_meta, twitter_ops, env_config


# Check the time
start = time.time()
now = datetime.datetime.now()


def signal_handler(sig, frame):
    """Handle interrupt signals, eg ctrl-c (and other kill signals).
    
    Exiting more abruptly can leave MongoDB running, which can cause issues,
    so Mongo is asked to stop
    """
    print(f"\n\nJust a second while I try to exit gracefully...")
    with open(status_file, 'w+') as status:
        status.write(f"Epicosm is currently idle, but was interruped by user on last run.\nThe most recent harvest\
 was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\n")
    mongo_ops.stop_mongo()
    sys.exit()

                     
# setup signal handler
signal.signal(signal.SIGINT, signal_handler)


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

# Set paths as instance of EnvironmentConfig
env = env_config.EnvironmentConfig()

# Check user list exists and get it
if not os.path.exists(env.run_folder + '/user_list'):
    print(f"USAGE: please provide a list of users to follow, named 'user_list'.")
    sys.exit()
number_of_users_provided = sum(1 for line_exists in open(env.run_folder + '/user_list') if line_exists)
screen_names = list(dict.fromkeys(line.strip() for line in open(env.run_folder + '/user_list'))) # remove duplicates
screen_names = [name for name in screen_names if name] # remove empty lines

# Check or make directory structure
if not os.path.exists(env.run_folder + '/db'):
    print(f"MongoDB database folder seems absent, creating folder...")
    os.makedirs(env.run_folder + '/db')
if not os.path.exists(env.run_folder + '/db_logs'):
    print(f"DB log folder seems absent, creating folder...")
    os.makedirs(env.run_folder + '/db_logs')
if not os.path.exists(env.run_folder + '/epicosm_logs'):
    print(f"Epicosm log folder seems absent, creating folder...")
    os.makedirs(env.run_folder + '/epicosm_logs')


############
## run it ##
############

if __name__ == '__main__':

    try:
        # set up logging
        epicosm_meta.logger_setup(env.epicosm_log_filename)
        # connect to Twitter API
        twitter_ops.authorise()
        # start mongodb
        mongo_ops.start_mongo(mongod_executable_path,
                              env.db_path,
                              env.db_log_filename)
        # modify status file
        epicosm_meta.status_up(env.status_file)
        # tidy up the database for better efficiency
        mongo_ops.index_mongo(env.run_folder)
        # get persistent user ids from screen names
        twitter_ops.lookup_users(env.run_folder, screen_names)
        # get tweets for each user and archive in mongodb
        twitter_ops.harvest(env.run_folder)
        # if user wants the friend list, make it
        # !!! this is very slow, so is an option
        if '--get_following' in sys.argv:
            twitter_ops.get_following(env.run_folder)
        # create CSV file
        mongo_ops.export_csv(mongoexport_executable_path, env.csv_filename)
        # create JSON file
        # !!! this is big, slow and fields cannot be specified, so an option
        if '--json' in sys.argv:
            mongo_ops.export_json(mongoexport_executable_path, env.json_filename)
        # backup database into BSON
        mongo_ops.backup_db(mongodump_executable_path, env.database_dump_path)
        # modify status file
        epicosm_meta.status_down(env.status_file, env.run_folder)
        # shut down mongodb
        mongo_ops.stop_mongo()

        print(f"\nAll done, Epicosm finished at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}, taking around {int(round((time.time() - start) / 60))} minutes.")
    except:
        pass
