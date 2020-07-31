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

    print("Epicosm unning as", run_method)


############
## run it ##
############

def main():


    # check running method
    native_or_compiled()
    # check environment
    mongod_executable_path, mongoexport_executable_path, mongodump_executable_path, screen_names = epicosm_meta.check_env()
    epicosm_meta.check_env()
    # set up logging
    epicosm_meta.logger_setup(env.epicosm_log_filename)
    # setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    # verify credentials
    credentials = twitter_ops.get_credentials()
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
    mongo_ops.stop_mongo(env.db_path)

    print(f"Scheduled task finished at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}. Epicosm has been up for about {int(round((time.time() - start)) / 86400 )} days.")


if __name__ == '__main__':

    if ("--repeat" in sys.argv):
        main()
        schedule.every(3).days.at("06:00").do(main)
        while True:
            schedule.run_pending()
            time.sleep(15)
    else:
        main()

