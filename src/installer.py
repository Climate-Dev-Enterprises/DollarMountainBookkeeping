import platform
import os
import logging
import schedule
import time
import subprocess

from crontab import CronTab

class Installer:

    def __init__(self, reinstall=None):
        self.os = platform.system()
        self.reinstall = reinstall
        self.working_directory = os.getcwd()

    def install(self):
        '''
        We're going to create a lock file anytime the install is done
        This let's us know we did the install already and can skip this if the file exists
        '''
        lock_file = 'install.lock'
        if os.path.exists(lock_file) and not self.reinstall:
            logging.warning('We have already done the install. Rerun with --reinstall if you want to reinstall the software')
            return
        elif self.reinstall:
            print('Reinstall triggered...')
            os.remove(lock_file)
        else:
            print('Installing...')

        with open(lock_file, 'w+') as f:
            pass # Write file, but it's contents are empty

        self.build_inputs()

        if self.os and self.os == 'Windows':
            self.build_task_scheduler_jobs()
        else:
            self.build_cronjobs()

        print('Install completed!')

    def build_inputs(self):
        '''
        This gives the inputs required to tell the scheduler what to run and when
        If any scripts get added, they should be built in here
        '''
        # Get the cron job schedule from the user
        self.run_times = input('Enter the times you want this script to run on a 24 hour clock (e.g. 01 is 1 am, 13 is 1 pm) separated by a comma \n').split(',')
        for run_time in self.run_times:
            try:
                assert(len(run_time) in [1, 2])
                assert(int(run_time) < 24)
                assert(int(run_time) >= 0)
            except (AssertionError, ValueError):
                raise Exception('The values for the scheduler must be integers between 0 and 23 representing hours of the day')

        # Choose scripts
        while True:
            self.run_chow_now = input('Would you like to schedule the chow now script? Enter y for yes or n for n \n')
            if self.run_chow_now == 'y' or self.run_chow_now == 'n':
                break
            else:
                print('Pleae enter y for yes or n for no')

        while True:
            self.run_journals = input('Would you like to schedule the journal builder script? Enter y for yes or n for n \n')
            if self.run_journals == 'y' or self.run_journals == 'n':
                break
            else:
                print('Pleae enter y for yes or n for no')

        # Add any other scripts here in the same pattern
        return

    def build_cronjobs(self):
        '''
        On linux systems, create a cronjob in the crontab using crontab library
        This defaults to running on the current user
        This also comes with logging out of the box using the existing log file directory provided in the repo

        NOTE: This comes with the ability to edit the cronfile out of the box by chmodding the contab
        If you don not want this, comment this section out
        '''
        subprocess.call(['sudo chmod 2755 /usr/bin/crontab'], shell=True)

        cron = CronTab(user=True)

        for run_time in self.run_times:
            if self.run_chow_now:
                job = cron.new(command=f'{self.working_directory}/autorun/chow_now_auto.sh >> {self.working_directory}/../logs/chow_now_auto.log 2>&1')
                job.minute.on(0)
                job.hour.on(run_time)

            if self.run_journals:
                # This job requires a date argument, but cron can except the current date as an argument
                job = cron.new(command=f'{self.working_directory}/autorun/data_from_journal_auto.sh $(date +%Y%m%d) >> {self.working_directory}/../logs/journal_auto.log 2>&1')
                job.minute.on(0)
                job.hour.on(run_time)
        cron.write()

    def build_task_scheduler_jobs(self):
        '''
        For windows, add the jobs to task scheduler as cron doesn't exist there
        There are some painful to use libraries, but we can also just run a command here
        '''
        for run_time in self.run_times:
            if self.run_chow_now:
                os.system(rf'SchTasks /Create /SC DAILY /TN "My Task" /TR "{self.working_directory}/autorun/chow_now_auto.sh" /ST {run_time}:00')
            if self.run_journals:
                os.system(rf'SchTasks /Create /SC DAILY /TN "My Task" /TR "{self.working_directory}/autorun/data_from_journal_auto.sh $(date +%Y%m%d)" /ST {run_time}:00')
