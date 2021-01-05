import sys
import signal
import argparse
import subprocess

from modules import mongo_ops, epicosm_meta, twitter_ops, nlp_ops, env_config, mongodb_config

def args_setup():

    parser = argparse.ArgumentParser(description="Epidemiology of Cohort Social Media - Natural Language Processing",
                                     epilog="Example: python3 epicosm_nlp.py --vader --labmt")
    parser.add_argument("--vader", action="store_true",
      help="Harvest tweets from all users from a file called user_list (provided by you) with a single user per line.")
    parser.add_argument("--labmt", action="store_true",
      help="Create a database of the users that are being followed by the accounts in your user_list. (This process can be very slow, especially if your users are prolific followers.)")
    parser.add_argument("--liwc", action="store_true",
      help="Repeat the harvest every 72 hours. This process will need to be put to the background to free your terminal prompt.")
    parser.add_argument("--textblob", action="store_true",
      help="If you have a new user_list, this will tell Epicosm to switch to this list.")
    parser.add_argument("--insert_groundtruth", action="store_true",
      help="Start the MongoDB daemon in this folder, but don't run any Epicosm processes.")

    args = parser.parse_args()

    return parser, args


def main():

    # Set paths as instance of EnvironmentConfig
    env = env_config.EnvironmentConfig()

    try:
        subprocess.check_output(["pgrep", "mongod"])
        print(f"MongoDB looks up.")
    except subprocess.CalledProcessError:
        print(f"MongoDB does not appear to be running here. You can start MongoDB with")
        print(f"python3 epicosm.py --start_db")
        sys.exit(0)

    if len(sys.argv) < 2:
            parser.print_help()
            sys.exit(0)

    # check running method
    epicosm_meta.native_or_compiled()

    # check environment
    mongod_executable_path, mongoexport_executable_path, mongodump_executable_path, screen_names = epicosm_meta.check_env()

    # setup signal handler
    signal.signal(signal.SIGINT, epicosm_meta.signal_handler)

    # check size of collection
    total_records = mongodb_config.collection.estimated_document_count()
    if total_records == 0:
        print(f"The database seems empty. Nothing to do.")
        sys.exit(0)

    if args.vader:
        nlp_ops.mongo_vader(mongodb_config.db, total_records)

    if args.labmt:
        nlp_ops.mongo_labMT(mongodb_config.db, total_records)

    if args.textblob:
        nlp_ops.mongo_textblob(mongodb_config.db, total_records)

    if args.liwc:
        nlp_ops.mongo_liwc(mongodb_config.db, total_records)

    # backup database into BSON
    mongo_ops.backup_db(mongodump_executable_path,
                        env.database_dump_path,
                        env.epicosm_log_filename,
                        env.processtime)


if __name__ == "__main__":

    parser, args = args_setup()

    main()

