# DollarMountainBookkeeping

## Starting the data jobs

We use shell scripts to trigger the bookkeeping jobs. The process cna be started using any of the following:

1. Run the install script to create a daily task schedule. On windows this creates a task in windows task scheduler. On all other operating systems, this makes a cronjob. This is preferred for less technical users that just want this to run automatically.
2. Navigate to src/autorun and run the shell scripts directly. They can be triggered with an argument for the date to run it

The following sections breakdown the features included in this library

## Installer
To run the installer, you must complete the following base requirements:

- Valid Python installation of at least version 3.10
- Must install Anaconda for windows (https://www.anaconda.com/docs/getting-started/anaconda/install)

Ideally, I would recommend installing Cygwin as the works around a lot of the windows funkiness as well (https://cygwin.org/install.html)

You can also get the built in Windows Subsystem for Linux (wsl2) from the app store. This is more modern and comprehensive, and thus easier to use. It is heavier weight though

Next, download the full respository here from the github page. If you're on windows, download it to the following path: C://ProgramFiles/DollarMountainBookkeeping

Once downloaded, you should be able to install the softwarfe by navigating to C://ProgramFiles/DollarMountainBookkeeping/src/autorun and running install.bat (on windows) or install.sh (all others) as an admin

NOTE: All windows installations are still in alpha and the install process will likely be improved in future releases

This will install the jobs to automate the data retreival, however the individual jobs can also be run on demand if you wish

## The data repository
All data is stored in the /data directory within the software. All output files are in the root of that directory, named by day

## Chownow Job
Accessed via the chow_now_auto.sh (linux) and chow_now.bat (windows) script. This rebuilds the chow now data files as csv so 1 software can be used to compile all of it. Look for the results in ChowNow_JE_Output.csv

## Journal job
These are for the Vagaro jobs, here classified as "journal entries"

This service cleans the data files and fills in the missing entries within the data table for you before compiling into a final csv report that can be directly imported into Quickbooks

TODO: This should upload to Quickbooks automatically in a future release

Accessed via the data_from_journal_auto.sh (linux) and data_from_journal.bat (windows) scripts
