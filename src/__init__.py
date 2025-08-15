import logging

from args import args
from data_importer import DataImporter

if __name__ == '__main__':
    logging.info('Launched Climate Dev CSV tool')

    # Chow now data importer
    if args.is_chow_now:
        data_importer = DataImporter(args)
        print(data_importer.file_path)

        data_importer.load_data()

    # Import from journal job
    if args.import_journal:
        pass
