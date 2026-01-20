# This file loads in data from a journal entry and translates it into the needed csv output file format

import pandas as pd
import numpy as np
import logging
import os

from datetime import datetime

from data_row_builder import DataRowFactory

class JournalDataImporter:

    def __init__(self, args):
        self.date = args.date
        self.file_path = args.file_path
        self.journal_keys = args.journal_keys.split(',')
        self.file_list = self.load_source_data_file()
        self.output_file = f'../data/{self.date}-journal_entry.csv'
        self.journal_date = datetime.strptime(str(self.date), "%Y%m%d").strftime("%m/%d/%Y")

    def load_source_data_file(self):
        '''
        This scans the file tree given in the input file path for the needed TL and DR xlsx files
        Those files are appended to the file list so that we can generate a final composite file
        '''
        file_list = []
        if not os.path.exists(self.file_path):
            raise Exception('The specified file path {self.file_path} was not found')

        # Walk the data directory and grab all DR and TL xlsx files that match that date
        for root, dirs, files in os.walk(self.file_path):
            for name in files:
                if name.endswith('xlsx'):
                    if name.startswith(f'{self.date}-DR') or name.startswith(f'{self.date}-TL'):
                        fid = os.path.join(root, name)
                        file_list.append(fid)
        return file_list

    def maybe_load_discounts(self, transaction_df):
        '''
        Vagaro does a terrible job with the data, so this helper function fixes it
        The column "disc" for discount should be the difference between the amount paid and the price
        Where here the discount is only applied if the amount paid is less than the price
        NOTE: The amount paid may be MORE than the price. This indicates a tip

        :param transaction_df: The df containing the broken data from Vagaro
        '''
        if 'Price' in transaction_df and 'Amt paid' in transaction_df:
            for index, entry in transaction_df.iterrows():
                if 'Tip' in entry:
                    discount = entry['Price'] + entry['Tip'] - entry['Amt paid']
                else:
                    discount = entry['Price'] - entry['Amt paid']
                if discount > 0:
                    entry['Disc'] = discount
                transaction_df.loc[index] = entry
        else:
            logging.warning('The data here does not have the required columns for the discount to be calculated')
        return transaction_df

    def load_apply_discounts_column(self, transaction_df, deposit_df):
        '''
        This adds a column to the transactions  dataframe that indicates if a vdiscount should be applied
        This runs over a range, which solves the problem of the ghost transactions

        :param transaction_df: This is the dataframe containing all transaction rows
        :param deposit_df: This is the datafram containg all deposit rows
        '''
        unique_transactions = deposit_df['TranNum'].unique()
        common_transactions = transaction_df[transaction_df['Transaction ID'].isin(unique_transactions)]
        matching_indices = range(common_transactions.index[0], common_transactions.index[-1] + 1)
        discount_fields = []
        for index, entry in transaction_df.iterrows():
            if index in matching_indices:
                entry['Apply Discount'] = 'yes'
            else:
                entry['Apply Discount'] = 'no'
            discount_fields.append(entry['Apply Discount'])
        transaction_df['Apply Discount'] = discount_fields
        return transaction_df

    def build_composite_dataframe(self):
        '''
        This loads in the relevant transactions and deposits files for the given dates

        Then, we build the dataframe out to house the data with the given rules:
            # TODO: once you understand the rules, fill this out
        '''
        self.output_df = pd.DataFrame(columns=self.journal_keys)
        for file in self.file_list:
            if '-TL' in file:
                # Then it's a transaction file
                transaction_df = pd.read_excel(file, engine='openpyxl', skiprows=22)
            elif '-DR' in file:
                # Then it's a deposit file
                deposit_df = pd.read_excel(file, engine='openpyxl')
            else:
                logging.warning(f'An unknown file {file} was found that does not match a deposit or transaction file. Skipping.')
                continue

        # Remove currency sign and change () to negative
        self.excel_currency_to_signed_float(deposit_df)
        self.excel_currency_to_signed_float(transaction_df)

        # Fix broken discount data
        transaction_df = self.maybe_load_discounts(transaction_df)

        # Using Katelyn's term for these, she calls there "ghost transactions"
        # We have to find all of transactions that overlap between the 2 reports
        # The ghost transactions are every row in between
        # We'll do this by adding a new column because the data really should tell us this
        transaction_df = self.load_apply_discounts_column(transaction_df, deposit_df)

        # We need to ensure that debits are only written once for a single debit transaction
        write_debits = True
        has_single_debit = False
        raw_profit = 0

        for index, entry in transaction_df.iterrows():
            # Each row may have profit and fee information associated with it
            # The code at the end ensures these are separate row numbers on the final csv
            if has_single_debit is False:
                data_row_factory = DataRowFactory()

            # Match the transaction ids between the 2 dataframes
            transaction_number = entry['Transaction ID']
            transaction_row = deposit_df.loc[deposit_df['TranNum'] == transaction_number]

            if transaction_row.empty and has_single_debit is False:
                # FIXME: This may not be right. I'm assuming some logic applies where a profit must be counted even if no fees
                # That profit row must, however, be greater than 0 or the row is skipped
                if entry['Transaction Type'] == 'Membership':
                    credits = entry['Qty'] * entry['Price']
                    if credits > 0:
                        membership_row = data_row_factory.build_data_row('membership')
                        membership_row["Credits"] = credits

            else:
                # It's on both reports, so we have a deposit to account for
                # The total amount for this transaction is the fee from this row + (minus) any net amounts less than 0
                # TODO: There can be more than 1 of the net negative rows and this needs to be tested
                negative_net_row = deposit_df.loc[deposit_df['NetAmount'].astype(str).astype(float) < 0]
                if negative_net_row.empty:
                    raw_debit = round(sum(deposit_df['Fee']), 2)
                    has_single_debit = True
                else:
                    raw_debit = sum([transaction_row['Fee'].iloc[0], negative_net_row['NetAmount'].iloc[0]])
                net_amount = str(raw_debit).replace('-', '-$')

                if write_debits:
                    fee_row = data_row_factory.build_data_row('vagaro')
                    fee_row["Debits"] = net_amount

                # We have the fee, now check for a profit on this transaction
                # Single debits have "special" rules where we just want to sum the amounts and tips
                if entry['Transaction Type'] in ['Services', 'Service Add-on'] and entry['Apply Discount'] == 'yes':
                    # Profits from services as its own row
                    if 'profit_row' in locals() and 'Credits' in profit_row:
                        profit_row["Credits"] = float(str(profit_row['Credits']).replace('$', '')) + entry['Price']
                    else:
                        profit_row = data_row_factory.build_data_row('income')
                        profit_row["Credits"] = entry['Price']

                    # Tips applied as its own row
                    if 'tips_row' in locals() and 'Credits' in tips_row:
                        tips_row["Credits"] = float(str(tips_row['Credits']).replace('$', '')) + entry['Tip']
                    elif entry['Tip']:
                        tips_row = data_row_factory.build_data_row('tips')
                        tips_row["Credits"] = entry['Tip']

                    # Discounts applied as their own row (NOTE: discounts are negative by convention)
                    if 'discounts_row' in locals() and 'Debits' in discounts_row:
                        discounts_row["Debits"] = -float(str(-discounts_row['Debits']).replace('$', '')) - entry['Disc']
                    elif entry['Disc']:
                        discounts_row = data_row_factory.build_data_row('discount')
                        discounts_row["Debits"] = -entry['Disc']

                elif entry['Transaction Type'] == 'Membership' and entry['Apply Discount'] == 'yes':
                    # We'll use a raw_profit of 0 to cover cases where there is no profit in this transaction
                    # Convert the profit amount back to currency (.00 on whole values)
                    raw_profit = entry['Qty'] * entry['Price']
                    if raw_profit > 0:
                        profit_amount = f"${str(raw_profit)}"
                        if '.' not in profit_amount:
                            profit_amount += '.00'
                    if 'membership_row' in locals() and 'Credits' in membership_row:
                        membership_row["Credits"] = float(str(membership_row['Credits']).replace('$', '')) + raw_profit
                    else:
                        membership_row = data_row_factory.build_data_row('membership')
                        membership_row["Credits"] = profit_amount

                # If we totaled the debits, then don't write again
                if has_single_debit:
                    write_debits = False

            # If we have just a single debit, aggregate sum the values rather than splitting
            if has_single_debit and index < len(transaction_df) -1:
                continue

            # Add new row containing every record we got on this pass
            data_types = [str(x) for x in data_row_factory.data_types]
            data_set = []
            total_debits = 0
            total_credits = 0
            for data_type in data_types:
                if data_type == 'vagaro':
                    data_set.append(fee_row)
                    total_debits += float(str(fee_row["Debits"]).replace("$",""))
                elif data_type == 'income':
                    data_set.append(profit_row)
                    total_credits += float(str(profit_row["Credits"]).replace("$",""))
                elif data_type == 'tips':
                    data_set.append(tips_row)
                    total_credits += float(str(tips_row["Credits"]).replace("$",""))
                elif data_type == 'membership':
                    data_set.append(membership_row)
                    total_credits += float(str(membership_row["Credits"]).replace("$",""))
                elif data_type == 'discount':
                    data_set.append(discounts_row)
                    total_debits += float(str(discounts_row["Debits"]).replace("$",""))

            # Totals row should always be present at the end
             # NOTE: These are inverted because that's how banks handle debits/credits
            total_amount = total_credits + total_debits
            if total_amount:
                totals_row = data_row_factory.build_data_row('')
                if total_amount < 0:
                    totals_row["Credits"] = total_amount
                else:
                    totals_row["Debits"] = total_amount
                data_set.append(totals_row)

            for data_row in data_set:
                data_row['Journal No.'] = self.date
                data_row['Journal Date'] = self.journal_date
                data_row['Credits'] = f'${str(data_row["Credits"]).replace("$", "")}' if data_row["Credits"] else ""
                data_row['Debits'] = f'${str(data_row["Debits"]).replace("$", "")}' if data_row["Debits"] else ""
                new_row_df = pd.DataFrame([data_row])
                self.output_df = pd.concat([self.output_df , new_row_df], ignore_index=True)

            # Garbage collection
            del data_row_factory

        # Write to final csv file
        self.write_csv()

    def write_csv(self):
        '''
        Given a compiled dataframe, write the result to csv, logging any errors
        '''
        try:
            self.output_df.to_csv(self.output_file, index=False)
            logging.info(f'Output file written: {self.output_file}')
        except Exception as e:
            logging.error(f'Unable to write to file: {e}')

    def excel_currency_to_signed_float(self, df):
        '''
        This takes an excel value that contains $ and () and converts it to signed float we can use
        '''
        for column in df.columns:
            try:
                df[column] = df[column].str.replace('$', '', regex=False)
                df[column] = df[column].apply(lambda x: -float(x.strip('()')) if '(' in x else float(x))
            except (AttributeError, ValueError, TypeError):
                # Not a float, leave alone
                continue

