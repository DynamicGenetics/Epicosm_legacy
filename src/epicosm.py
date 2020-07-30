# -*- coding: utf-8 -*-

import os
import sys
import time
import datetime
import subprocess
import signal
import schedule

# from ./modules
from modules import mongo_ops, epicosm_meta, twitter_ops, env_config


# Check the time
start = time.time()
now = datetime.datetime.now()

# Set paths as instance of EnvironmentConfig
env = env_config.EnvironmentConfig()

def signal_handler(sig, frame):

    """Handle interrupt signals, eg ctrl-c (and other kill signals).
    
    Exiting more abruptly can leave MongoDB running, which can cause issues,
    so Mongo is asked to stop
    """
    status_file = env.status_file
    print(f"Just a second while I try to exit gracefully...")
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

# Check user list exists and get it
if not os.path.exists(env.run_folder + '/user_list'):
    print(f"USAGE: please provide a list of users to follow, named 'user_list'. Stopping.")
    sys.exit()
number_of_users_provided = sum(1 for line_exists in open(env.run_folder + '/user_list') if line_exists)
screen_names = list(dict.fromkeys(line.strip() for line in open(env.run_folder + '/user_list'))) # remove duplicates
screen_names = [name for name in screen_names if name] # remove empty lines

# Check credentials exist
credentials = twitter_ops.get_credentials()

# Check or make directory structure
if not os.path.exists(env.run_folder + '/db'):
    print(f"Looks like your first run here: making folders.")
    os.makedirs(env.run_folder + '/db')
if not os.path.exists(env.run_folder + '/db_logs'):
    os.makedirs(env.run_folder + '/db_logs')
if not os.path.exists(env.run_folder + '/epicosm_logs'):
    os.makedirs(env.run_folder + '/epicosm_logs')


############
## run it ##
############

def main():

    # set up logging
    epicosm_meta.logger_setup(env.epicosm_log_filename)
    # start mongodb
    mongo_ops.start_mongo(mongod_executable_path,
                          env.db_path,
                          env.db_log_filename,
                          env.epicosm_log_filename)
    # modify status file
    epicosm_meta.status_up(env.status_file)
    # tidy up the database for better efficiency
    mongo_ops.index_mongo(env.run_folder)
    # get persistent user ids from screen names
    twitter_ops.lookup_users(env.run_folder, screen_names, credentials)
    # get tweets for each user and archive in mongodb
    twitter_ops.harvest(env.run_folder, credentials)
    # if user wants the friend list, make it
    # !!! this is very slow, so is an option
    if '--get_following' in sys.argv:
        twitter_ops.get_following(env.run_folder, credentials)
    # create CSV file
    mongo_ops.export_csv(mongoexport_executable_path,
                         env.csv_filename,
                         env.epicosm_log_filename)
    # create JSON file
    # !!! this is big, slow and fields cannot be specified, so an option
    if '--json' in sys.argv:
        mongo_ops.export_json(mongoexport_executable_path,
                              env.json_filename,
                              env.epicosm_log_filename)
    # backup database into BSON
    mongo_ops.backup_db(mongodump_executable_path,
                        env.database_dump_path,
                        env.epicosm_log_filename)
    # modify status file
    epicosm_meta.status_down(env.status_file, env.run_folder)
    # shut down mongodb
    mongo_ops.stop_mongo()

    print(f"Scheduled task finished at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}. Epicosm has been up for about {int(round((time.time() - start)) / 86400 )} days.")


if __name__ == '__main__':

    if ("--once" in sys.argv):
        main()
    else:
        main()
        schedule.every(3).days.at("06:00").do(main)
        while True:
            schedule.run_pending()
            time.sleep(15)

