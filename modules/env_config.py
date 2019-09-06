import os
from datetime import datetime


DEFAULT_RUN_FOLDER = '/root/host_interface/'


class EnvironmentConfig:
    """"""

    def __init__(self):
        if os.path.exists('./dockerenv'):
            self._runfolder = DEFAULT_RUN_FOLDER
        else:
            self._runfolder = os.getcwd()
        self._current_time = datetime.now()

    @property
    def logfilename(self):
        return '{}.log'.format(self._current_time.strftime('%H:%M:%S_%d-%m-%Y'))

    @property
    def run_folder(self):
        return self._runfolder

    @property
    def status_file(self):
        return os.path.join(self.run_folder, 'STATUS')

    @property
    def db_log_filename(self):
        return os.path.join(self.run_folder, 'db_logs', self.logfilename)

    @property
    def db_path(self):
        db_path = os.path.join(self.run_folder, 'db')
        os.makedirs(db_path, exist_ok=True)
        return db_path

    @property
    def csv_filename(self):
        return os.path.join(self.run_folder, 'output', 'csv', self.logfilename)

    @property
    def epicosm_log_filename(self):
        return os.path.join(self.run_folder, 'epicosm_logs', self.logfilename)

    @property
    def database_dump_path(self):
        return os.path.join(self.run_folder, 'output')

if __name__ == '__main__':
    env_config = EnvironmentConfig()



