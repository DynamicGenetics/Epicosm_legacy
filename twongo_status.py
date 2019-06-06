import datetime
import os


def status_up(collection, status_file):
    tweet_count = collection.count_documents({})
    with open(status_file, 'w+') as status:
        status.write(f"Twongo is currently running.\nThis process started at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\nThe database currently contains {tweet_count} tweets.\n")


def status_down(collection, status_file, run_folder):
    tweet_count = collection.count_documents({})
    with open(status_file, 'w+') as status:
        if os.path.isfile(run_folder + '.frequency'):
            frequency = open(run_folder + '.frequency', 'r').read()
            next_harvest = (datetime.datetime.now() + datetime.timedelta(hours = int(frequency))).strftime('%H:%M:%S_%d-%m-%Y')
            status.write(f"Twongo is currently idle.\nThe most recent harvest was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\nNext harvest is scheduled for {next_harvest}\nThe database currently contains {tweet_count} tweets.\n")
        else:
            status.write(f"Twongo is currently idle.\nThe most recent harvest was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\nThe database currently contains {tweet_count} tweets.\n")