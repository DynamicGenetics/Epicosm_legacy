import os
import sys
from datetime import datetime


DEFAULT_RUN_FOLDER = '/root/host_interface/'


class EnvironmentConfig:
    """Detects if environment is interactive or in Docker container.
    
    Returns the paths of files and executables relevant to that environment
    """

    def __init__(self):
        if os.path.exists('./dockerenv'):
            self._runfolder = DEFAULT_RUN_FOLDER
        else:
            self._runfolder = os.getcwd()
        self._current_time = datetime.now()

    @property
    def log_datetime(self):
        return '{}.log'.format(self._current_time.strftime('%H:%M:%S_%d-%m-%Y'))

    @property
    def csv_datetime(self):
        return '{}.csv'.format(self._current_time.strftime('%H:%M:%S_%d-%m-%Y'))

    @property
    def json_datetime(self):
        return '{}.json'.format(self._current_time.strftime('%H:%M:%S_%d-%m-%Y'))

    @property
    def run_folder(self):
        return self._runfolder

    @property
    def status_file(self):
        return os.path.join(self.run_folder, 'STATUS')

    @property
    def db_log_filename(self):
        return os.path.join(self.run_folder, 'db_logs', self.log_datetime)

    @property
    def db_path(self):
        db_path = os.path.join(self.run_folder, 'db')
        os.makedirs(db_path, exist_ok=True)
        return db_path

    @property
    def csv_filename(self):
        return os.path.join(self.run_folder, 'output', 'csv', self.csv_datetime)

    @property
    def json_filename(self):
        return os.path.join(self.run_folder, 'output', 'json', self.json_datetime)

    @property
    def epicosm_log_filename(self):
        return os.path.join(self.run_folder, 'epicosm_logs', self.log_datetime)

    @property
    def database_dump_path(self):
        return os.path.join(self.run_folder, 'output')

