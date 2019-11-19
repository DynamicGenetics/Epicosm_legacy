import datetime
import os
import pymongo
import sys
import logging


def logger_setup(epicosm_log_filename):
    ## Set up logging
    class StreamToLogger(object):
        
        """
        Write chatter to logfile.
        """
        
        def __init__(self, logger, log_level=logging.INFO):
            self.logger = logger
            self.log_level = log_level
            self.linebuf = ''

        def write(self, buf):
            for line in buf.rstrip().splitlines():
                self.logger.log(self.log_level, line.rstrip())

        def flush(self):
            pass

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
                        filename = epicosm_log_filename,
                        filemode='a')
    stdout_logger = logging.getLogger('STDOUT')
    sl = StreamToLogger(stdout_logger, logging.INFO)
    sys.stdout = sl
    stderr_logger = logging.getLogger('STDERR')
    sl = StreamToLogger(stderr_logger, logging.ERROR)
    sys.stderr = sl


def status_up(status_file):
    
    """ Update STATUS file in run folder to notify when running.
    
    Does a quick count of the current database,
    and rewrite the STATUS file to say that process is in progress."""
    
    client = pymongo.MongoClient('localhost', 27017)
    db = client.twitter_db
    collection = db.tweets
    tweet_count = collection.count_documents({})
    with open(status_file, 'w+') as status:
        status.write(f"Epicosm is currently running.\nThis process started at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\n")
        if tweet_count > 0:
            status.write(f"The database currently contains {tweet_count} tweets.\n")


def status_down(status_file, run_folder):

    """ Update STATUS file in run folder to notify when idle, and next run.
                     
    Does a quick count of the current database,
    and rewrite the STATUS file to say that process is in progress."""

    client = pymongo.MongoClient('localhost', 27017)
    db = client.twitter_db
    collection = db.tweets
    tweet_count = collection.count_documents({})
    with open(status_file, 'w+') as status:
        if os.path.isfile(run_folder + '.frequency'):
            frequency = open(run_folder + '.frequency', 'r').read()
            next_harvest = (datetime.datetime.now() + datetime.timedelta(hours = int(frequency))).strftime('%H:%M:%S_%d-%m-%Y')
            status.write(f"Epicosm is currently idle.\nThe most recent harvest was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\nNext harvest is scheduled for {next_harvest}\nThe database currently contains {tweet_count} tweets.\n")
        else:
            status.write(f"Epicosm is currently idle.\nThe most recent harvest was at {datetime.datetime.now().strftime('%H:%M:%S_%d-%m-%Y')}\nThe database currently contains {tweet_count} tweets.\n")

