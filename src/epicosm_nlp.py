import sys
import signal

from modules import mongo_ops, epicosm_meta, twitter_ops, nlp_ops, env_config, mongodb_config


valid_args = ["--vader", "--labmt", "--textblob", "--liwc", "--insert_groundtruth"]


usage = ["Epicosm Natural Language Processing: usage (full details: dynamicgenetics.github.io/Epicosm/)\n\n" +
         "Please provide flags:\n\n" +
         "--insert_groundtruth  Provide a file of groundtruth values called\n" +
         "                      'groundtruth.csv' and insert these into the local database.\n\n" +
         "--liwc                Apply LIWC (Pennebaker et al 2015) analysis and append values\n" +
         "                      to the local database. You must have a LIWC dictionary int the\n" +
         "                      run folder, and provide this file's name as a flag.\n\n" +
         "--labmt               Apply labMT (Dodds & Danforth 2011) analysis and append values\n" +
         "                      to the local database.\n\n" +
         "--vader               Apply VADER (Hutto & Gilbert 2014) analysis and append values\n" +
         "                      to the local database.\n\n" +
         "--textblob            Apply TextBlob (github: @sloria) analysis and append values\n" +
         "                      to the local database.\n\n" +
         "--extract_emoji       [in development]\n\n" +
         "--groundtruth_delta   [in development]\n\n" +
         "--time_of_day         [in development]\n\n" +
         "Example of VADER analysis:\n" +
         "./epicosm_nlp_linux --vader\n\n" +
         "Example of LIWC analysis:\n" +
         "./epicosm_nlp_linux --liwc LIWC.dic\n\n" +
         "All sentiment analysis metrics are stored in the final field of each record,\n" +
         "under the 'epicosm' block.\n\n"]


def main():


    # print help message if no/wrong args provided
    if len(sys.argv) < 2 or not all(arg in valid_args for arg in sys.argv[1:]):
        print(*usage)
        sys.exit(0)

    # Set paths as instance of EnvironmentConfig
    env = env_config.EnvironmentConfig()

    # check running method
    epicosm_meta.native_or_compiled()

    # check environment
    mongod_executable_path, mongoexport_executable_path, mongodump_executable_path, screen_names = epicosm_meta.check_env()

    # setup signal handler
    signal.signal(signal.SIGINT, epicosm_meta.signal_handler)
 
    # start mongodb
    mongo_ops.start_mongo(mongod_executable_path,
                          env.db_path,
                          env.db_log_filename,
                          env.epicosm_log_filename)

    # check size of collection
    total_records = mongodb_config.collection.estimated_document_count()
    if total_records == 0:
        print(f"The database seems empty. Nothing to do.")
        mongo_ops.stop_mongo(env.db_path)
        sys.exit(0)
    
    if "--vader" in sys.argv:
        nlp_ops.mongo_vader(mongodb_config.db, total_records)
    
    if "--labmt" in sys.argv:
        nlp_ops.mongo_labMT(mongodb_config.db, total_records)
    
    if "--textblob" in sys.argv:
        nlp_ops.mongo_textblob(mongodb_config.db, total_records)

    if "--liwc" in sys.argv:
        nlp_ops.mongo_liwc(mongodb_config.db, total_records)
    
    # in development :)
    #nlp_ops.mongo_nlp_example(mongodb_config.db, total_records)
    #nlp_ops.mongo_insert_groundtruth(mongodb_config.db, total_records)
    #nlp_ops.mongo_groundtruth_delta(mongodb_config.db, senti_method)
    
    # backup database into BSON
    mongo_ops.backup_db(mongodump_executable_path,
                        env.database_dump_path,
                        env.epicosm_log_filename,
                        env.processtime)
    # shut down mongodb
    mongo_ops.stop_mongo(env.db_path)


if __name__ == "__main__":
    main()

