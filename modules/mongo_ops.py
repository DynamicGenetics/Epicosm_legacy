import os
import subprocess
import sys
import time
import psutil
import pymongo


def start_mongo(mongod_executable_path, db_path, db_log_filename):

    """start mongo daemon, unless it is already running"""

    def mongo_go():
        print(f"\nStarting the MongoDB daemon...\n")
        try:
            subprocess.Popen([mongod_executable_path, '--dbpath', db_path, '--logpath', db_log_filename])
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


def stop_mongo(client):

    """gracefully close the mongo daemon"""

    print(f"\nAsking MongoDB to close...")
    client.close()
    subprocess.call(['pkill', '-15', 'mongod'])
    timeout = 60
    while timeout > 0:
        try:
            subprocess.check_output(['pgrep', 'mongod'])
        except subprocess.CalledProcessError:
            print(f"\nOK, MongoDB daemon closed.")
            break
        if '--log' not in sys.argv:
            print(".", end='', flush=True)
        time.sleep(1)
        timeout -= 1
    if timeout == 0:
        print(f"\nMongoDB didn't respond to requests to close... be aware that MongoDB is still running.")


def index_mongo(run_folder, db):  # tidy up the database

    """tidy up the database so that upsert operations are faster"""

    if not os.path.isfile(run_folder + '/db/WiredTiger'):
        return
    print(f"\nIndexing MongoDB...")
    db.tweets.create_index([('id_str', pymongo.ASCENDING)], unique=True, dropDups=True)


def export_and_backup(mongoexport_executable_path, mongodump_executable_path, database_dump_path, csv_filename):

    """Export some fields from the tweets in MongoDB into a CSV file
    then backup and compress the database"""

    print(f"\nCreating CSV output file...")
    subprocess.call([mongoexport_executable_path, '--host=127.0.0.1', '--db', 'twitter_db', '--collection', 'tweets', '--type=csv', '--out', csv_filename, '--fields', 'user.id_str,id_str,created_at,full_text'])
#    subprocess.call([mongoexport_executable_path, '--host=127.0.0.1', '--db', 'twitter_db', '--collection', 'tweets', '--type=csv', '--out', csv_filename, '--fields', 'user.id_str,id_str,created_at,retweeted_status.full_text,full_text'])
    print(f'\nBacking up the database...')
    subprocess.call([mongodump_executable_path, '-o', database_dump_path, '--host=127.0.0.1'])
    subprocess.call(['chmod', '-R', '0755', database_dump_path]) # hand back access permissions to host

