# This file loads in all of the data and translates it in from various sources to the desired output
import pandas as pd
import logging
import os

from copy import deepcopy

class DataImporter:

    def __init__(self, args):
        '''
        Create the data file class from the argument list passed in

        See args.py or --help for documentation on the args
        '''
        self.output_file = args.output_file
        self.file_path = args.file_path
        self.journal_keys = args.journal_keys.split(',')
        self.accounts = args.accounts.split(',')
        self.date = args.date
        self.journal_entries = []

        if not self.output_file.endswith('.csv'):
            raise Exception(f"The output file must be a CSV. Given {self.output_file}")

    def build_row(self, row_data, debit=None, credit=None):
        '''
        Given a row of data, apply some operations to set it up for excel
        Every row should have either a debit or credit (but it need not have both)

        Row data is an array containing the following:
            - date
            - journal number
            - memo
            - account

        See args.py or --help for explanation on default accounts
        '''
        if not debit and not credit:
            return

        row = {}
        for index, entry in enumerate(row_data):
            row[self.journal_keys[index]] = entry

        if debit:
            row["Debits"] = debit
            print(row)

        if credit:
            row["Credits"] = credit
        return row


    def load_data(self):
        '''
        Prepare the journal data for load into excel
        '''
        if not os.path.exists(self.file_path):
            raise Exception(f"The file {self.file_path} is missing")
        try:
            self.df = pd.read_excel(self.file_path, engine='xlrd')
        except:
            logging.info("Old excel format detected, using xlrd engine to load data")
            self.df = pd.read_excel(self.file_path, engine='openpyxl')

        logging.info(f"Available columns: {self.df.columns.tolist()}")
        summary_rows = self.df[self.df["Daily Total"].notna()]

        for index, row in summary_rows.iterrows():
            disbursement_date_raw = row.get("Disbursement Date")
            if pd.isna(disbursement_date_raw):
                logging.warning("Skipping row with missing Disbursement Date.")
                continue

            try:
                date = pd.to_datetime(disbursement_date_raw).strftime("%m/%d/%Y")
                journal_number = f"CN - Dep - {date[:-5]}"
                memo = f"ChowNow Deposit {date}"
            except Exception as e:
                logging.error(f"kipping row with bad date format: {disbursement_date_raw} ({e})")
                continue

            # Extract data from the tow to perform calculations as needed
            subtotal = row.get("Subtotal", 0) or 0
            tip = row.get("In-house Tip", 0) or 0
            tax = row.get("Tax", 0) or 0
            discount = row.get("Discount", 0) or 0
            daily_total = row.get("Daily Total", 0) or 0
            refunds = row.get("Refund Amount", 0) or 0
            fees = (row.get("Transaction Fee", 0) or 0) + \
                (row.get("Finder's Fee", 0) or 0) + \
                (row.get("External Partner Fee", 0) or 0)
            sales_credit = subtotal + discount
            credits = [sales_credit, tip, fees, refunds, tax]

            rows_to_add = []
            for index, account in enumerate(self.accounts):
                row_data = [date, journal_number, memo, account]
                rows_to_add.append(self.build_row(row_data, credit=credits[index]))

            # Optional discounts- add only if provided
            row_data = [date, journal_number, memo]
            if discount > 0:
                discount_data = deepcopy(row_data)
                discount_data.append("02-006 Discount Income")
                rows_to_add.append(self.build_row(discount_data, debit=discount))

            # Set final account for debits
            row_data.append("00-001 BUSINESS CHECKING (0050) - 1")
            rows_to_add.append(self.build_row(row_data, debit=daily_total))

            # Set data in journal entries to add
            for row in rows_to_add:
                if row:
                    self.journal_entries.append(row)

    def write_output_file(self):
        '''
        Write to the final output file given by the input arguments
        Note the error is thrown in init if this is non csv as only csv is supported for now (sorry not sorry)
        '''
        try:
            pd.DataFrame(self.journal_entries).to_csv(self.output_file, index=False)
        except Exception as e:
            logging.error(f"There was an error writing the output file: {e}")
        print(f"\n✅ Finished! Journal entries saved to: {self.output_file}")
