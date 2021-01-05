import os
from datetime import datetime


DEFAULT_RUN_FOLDER = '/root/host_interface/'  # the docker volume folder


class EnvironmentConfig:

    """Have a look at the environment and set up paths to relevant locations.
    In particular, discerns if run is in docker container."""

    def __init__(self):
        if os.path.exists('./dockerenv'):
            self._runfolder = DEFAULT_RUN_FOLDER
        else:
            self._runfolder = os.getcwd()
        self._current_time = datetime.now()

    @property
    def processtime(self):
        return '{}'.format(self._current_time.strftime('%Y-%m-%d_%H:%M:%S'))

    @property
    def run_folder(self):
        return self._runfolder

    @property
    def status_file(self):
        return os.path.join(self.run_folder, 'STATUS')

    @property
    def latest_geotweet(self):
        return os.path.join(self.run_folder, 'latest_geotweet.csv')

    @property
    def db_log_filename(self):
        return os.path.join(self.run_folder, 'db_logs', self.processtime + ".log")

    @property
    def db_path(self):
        db_path = os.path.join(self.run_folder, 'db')
        os.makedirs(db_path, exist_ok=True)
        return db_path

    @property
    def csv_tweets_filename(self):
        return os.path.join(self.run_folder, 'output', 'csv', self.processtime + ".csv")

    @property
    def csv_friends_filename(self):
        return os.path.join(self.run_folder, 'output', 'csv', "friends" + self.processtime + ".csv")

    @property
    def epicosm_log_filename(self):
        return os.path.join(self.run_folder, 'epicosm_logs', self.processtime + ".log")

    @property
    def bson_backup_filename(self):
        return os.path.join(self.run_folder, "output", "twitter_db", self.processtime + ".bson")

    @property
    def database_dump_path(self):
        return os.path.join(self.run_folder, 'output')

