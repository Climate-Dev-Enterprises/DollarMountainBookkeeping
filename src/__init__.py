import logging
import sys

from args import args
from data_importer import DataImporter
from data_translator_from_journal import JournalDataImporter
from installer import Installer

if __name__ == '__main__':
    logging.info('Launched Climate Dev Bookkeeping tools')

    if args.install or args.reinstall:
        installer = Installer(reinstall = args.reinstall)
        installer.install()
        sys.exit()

    kill()
    # Check the date provided to ensure it is an integer in yyyymmdd format
    try:
        assert(len(str(args.date)) == 8)
    except AssertionError:
        raise Exception("The length of the date given is not correct6. Make sure it is in yyyymmdd format (e.g. 20251031)")

    # Chow now data importer
    if args.is_chow_now:
        data_importer = DataImporter(args)
        print(data_importer.file_path)

        data_importer.load_data()
        data_importer.write_output_file()

    # Import from journal job
    if args.import_journal:
        journal_data_importer = JournalDataImporter(args)

        journal_data_importer.build_composite_dataframe()
