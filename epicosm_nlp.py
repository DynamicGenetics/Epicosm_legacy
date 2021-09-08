
#~ Standard library imports
import os
import sys
import glob
import signal
import argparse
import subprocess

#~ Local application imports
from modules import (
    mongo_ops,
    epicosm_meta,
    twitter_ops,
    nlp_ops,
    env_config,
    mongodb_config)


def args_setup():

    parser = argparse.ArgumentParser(description="Epidemiology of Cohort Social Media - Natural Language Processing",
                                     epilog="Example: python3 epicosm_nlp.py --vader --labmt")
    parser.add_argument("--vader", action="store_true",
      help="Perform VADER NLP on each record in MongoDB.")
    parser.add_argument("--labmt", action="store_true",
      help="Perform LabMT NLP on each record in MongoDB.")
    parser.add_argument("--liwc", action="store_true",
      help="Perform LIWC NLP on each record in MongoDB. You will need an LIWC dictionary in your working folder, named LIWC.dic")
    parser.add_argument("--textblob", action="store_true",
      help="Perform Textblob NLP on each record in MongoDB.")
    parser.add_argument("--insert_groundtruth", action="store_true",
      help="Append groundtruth metrics to each record in MongoDB.")

    args = parser.parse_args()

    return parser, args


def main():

    #~ Set paths as instance of EnvironmentConfig
    env = env_config.EnvironmentConfig()

    try:
        subprocess.check_output(["pgrep", "mongod"])
        print(f"MongoDB identified as running.")
    except subprocess.CalledProcessError:
        print(f"MongoDB does not appear to be running here. You can start MongoDB with")
        print(f"python3 epicosm.py --start_db")
        sys.exit(0)

    if len(sys.argv) < 2:
            parser.print_help()
            sys.exit(0)

    #~ check running method
    epicosm_meta.native_or_compiled()

    #~ check environment
    mongod_executable_path, mongoexport_executable_path, mongodump_executable_path = epicosm_meta.check_env()

    #~ setup signal handler
    signal.signal(signal.SIGINT, epicosm_meta.signal_handler)

    #~ check size of collection
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

    #~ backup database into BSON
    mongo_ops.backup_db(mongodump_executable_path,
                        env.database_dump_path,
                        env.epicosm_log_filename,
                        env.processtime)

    #~ rotate backups - if there are more than 3, remove the oldest one
    current_backup_count = len([name for name in os.listdir(env.database_dump_path + "/twitter_db") if os.path.isfile(os.path.join(env.database_dump_path + "/twitter_db", name))])
    #~ each backup is one bson and one json of metadata, so 6 = 3 backups.
    if current_backup_count > 6:
        print("Rotating backups.")
        bu_list = glob.glob(env.database_dump_path + "/twitter_db/tweets*")
        bu_list.sort()
        #~ remove the oldest two, a bson and a json
        subprocess.call(["rm", bu_list[0]])
        subprocess.call(["rm", bu_list[1]])

if __name__ == "__main__":

    parser, args = args_setup()

    main()

