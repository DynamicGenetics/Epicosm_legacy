import datetime
import os


def status_up(collection, status_file):
    
    """ Update STATUS file in run folder to notify when running """
    
    tweet_count = collection.count_documents({})
    with open(status_file, 'w+') as status:
        status.write(f"Epicosm is currently running.\nThis process started at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\nThe database currently contains {tweet_count} tweets.\n")


def status_down(collection, status_file, run_folder):
                     
    """ Update STATUS file in run folder to notify when idle, and next run """
                     
    tweet_count = collection.count_documents({})
    with open(status_file, 'w+') as status:
        if os.path.isfile(run_folder + '.frequency'):
            frequency = open(run_folder + '.frequency', 'r').read()
            next_harvest = (datetime.datetime.now() + datetime.timedelta(hours = int(frequency))).strftime('%H:%M:%S_%d-%m-%Y')
            status.write(f"Epicosm is currently idle.\nThe most recent harvest was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\nNext harvest is scheduled for {next_harvest}\nThe database currently contains {tweet_count} tweets.\n")
        else:
            status.write(f"Epicosm is currently idle.\nThe most recent harvest was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\nThe database currently contains {tweet_count} tweets.\n")

 
