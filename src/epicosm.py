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

valid_args = ["--user_harvest", "--id_harvest", "--get_following",
              "--repeat", "--refresh", "--geo_harvest", "--sentiment_analysis"]

usage = ["Epicosm usage (full details: dynamicgenetics.github.io/Epicosm/)\n\n" + 
         "Please provide flags:\n\n" +
         "--user_harvest        Harvest tweets from all users from a file called user_list\n" +
         "                      (provided by you) with a single user per line.\n\n" + 
         "--id_harvest          Harvest tweets from all users from a file called user_list.ids\n" + 
         "                      with one Twitter account ID number per line.\n" +
         "                      (Epicosm can produce this after running with a user_list).\n\n" + 
         "--get_following       Create a database of the users that are\n" + 
         "                      being followed by the accounts in your user_list.\n" + 
         "                      (This process can be very slow, especially if\n" + 
         "                      your users are prolific followers.)\n" + 
         "                      If using with --repeat, will only be gathered once.\n\n" + 
         "--repeat              Iterate the user harvest every 3 days. This process will need to\n" 
         "                      be put to the background to free your terminal prompt,\n" + 
         "                      or to leave running while logged out.\n" + 
         "                      For example: nohup ./epicosm --user_harvest --repeat\n" +
         "                      (see documentation for more examples of running Epicosm.)\n\n" +  
         "--refresh             If you have a new user_list, this will tell Epicosm to\n" + 
         "                      take use this file as your updated user list.\n" + 
         "                      If using with --repeat, will only be gathered once.\n\n" + 
         "--geo_harvest         Launch a stream-listener, gathering tweets from a defined\n" + 
         "                      location file called \"geo_boxes.py\".\n" + 
         "                      This process will need be put to the background to free\n" + 
         "                      your terminal prompt or to leave running while logged out.\n" + 
         "                      (see documenation for examples and details.)\n\n" + 
         "--sentiment_analysis  Carry out a sentiment analysis on an existing\n" + 
         "                      database of tweets. See documentation for details.\n\n" + 
         "Typical example of an ongoing harvest:\n" + 
         "./epicosm --user_harvest --repeat\n\n"]


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

    print("Epicosm launching as", run_method)


############
## run it ##
############

def main():

    # print some guidance if no/wrong args provided
#    if len(sys.argv) < 2 or not any(arg in sys.argv[1:] for arg in valid_args):
    if len(sys.argv) < 2 or not any(arg in sys.argv[1:] for arg in valid_args):

        print(sys.argv[1:])
        print(*usage)
        sys.exit(0)

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
    if "--user_harvest" in sys.argv:
        twitter_ops.harvest(env.run_folder, credentials)
    # if user wants the friend list, make it
    if "--get_following" in sys.argv:
        twitter_ops.get_following(env.run_folder, credentials)
        sys.argv.remove("--get_following") # we only want to do this once
    # create CSV file
    mongo_ops.export_csv(mongoexport_executable_path,
                         env.csv_filename,
                         env.epicosm_log_filename)
    # create JSON file
    # !!! this is big, slow and fields cannot be specified
    if "--json" in sys.argv:
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

    print(f"Scheduled task finished at {datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}. Epicosm has been up for about {int(round((time.time() - start)) / 86400 )} days.")


if __name__ == "__main__":

    if ("--repeat" in sys.argv):
        main()
#        schedule.every(3).days.at("06:00").do(main)
        schedule.every(30).seconds.do(main)
        while True:
            schedule.run_pending()
            time.sleep(15)
    else:
        main()

