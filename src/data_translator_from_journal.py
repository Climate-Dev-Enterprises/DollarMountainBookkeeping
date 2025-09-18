# This file loads in data from a journal entry and translates it into the needed csv output file format

import pandas as pd
import numpy as np
import logging
import os

from datetime import datetime

class JournalDataImporter:

    def __init__(self, args):
        self.date = args.date
        self.file_path = args.file_path
        self.journal_keys = args.journal_keys.split(',')
        self.file_list = self.load_source_data_file()
        self.output_file = f'../data/{self.date}-journal_entry.csv'

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

        entry_number = 0 # This is the number of actual written rows in the final df
        for index, entry in transaction_df.iterrows():
            # Each row may have profit and fee information associated with it
            # The code at the end ensures these are separate row numbers on the final csv
            profit_row = {}
            fee_row = {}

            # Match the transaction ids between the 2 dataframes
            transaction_number = entry['Transaction ID']
            transaction_row = deposit_df.loc[deposit_df['TranNum'] == transaction_number]

            if transaction_row.empty:
                # FIXME: This may not be right. I'm assuming some logic applies where a profi must be counted even if no fees
                if entry['Transaction Type'] == 'Membership':
                    profit_row['Received From'] = 'Massage Therapy Customers'
                    profit_row['Account'] = '02-008 Membership Income'
                    profit_row['Description'] = 'Vagaro Merchant Services Depost'
                    profit_row['Payment Method'] = ''
                    profit_row['Ref No.'] = ''
                    profit_row['Amount'] = entry['Qty'] * entry['Price']

            else:
                # It's on both reports, so we have a depost to account for
                # The total amount for this transaction is the fee from this row + (minus) any net amounts less than 0
                # TODO: There can be more than 1 of the net negative rows and this needs to be tested
                negative_net_row = deposit_df.loc[deposit_df['NetAmount'].astype(str).astype(float) < 0]
                net_amount = str(sum([transaction_row['Fee'].iloc[0], negative_net_row['NetAmount'].iloc[0]])).replace('-', '-$')
                fee_row['Received From'] = 'Vagaro'
                fee_row['Account'] = '01-017 Vagaro Fees'
                fee_row['Description'] = 'Vagaro Merchant Services Depost'
                fee_row['Payment Method'] = ''
                fee_row['Ref No.'] = ''
                fee_row['Amount'] = net_amount

                # We have the fee, now check for a profit on this transaction
                if entry['Transaction Type'] == 'Membership':
                    profit_row['Received From'] = 'Massage Therapy Customers'
                    profit_row['Account'] = '02-008 Membership Income'
                    profit_row['Description'] = 'Vagaro Merchant Services Depost'
                    profit_row['Payment Method'] = ''
                    profit_row['Ref No.'] = ''

                    # Convert the profit amount back to currency (.00 on whole values)
                    profit_amount = f"${str(entry['Qty'] * entry['Price'])}"
                    if '.' not in profit_amount:
                        profit_amount += '.00'
                    profit_row['Amount'] = profit_amount

            # Add new row for every profit and fee record
            # Fees come 1st
            data_set = [fee_row, profit_row]
            for data_row in data_set:
                if data_row:
                    data_row['#'] = entry_number
                    new_row_df = pd.DataFrame([data_row])
                    self.output_df = pd.concat([self.output_df , new_row_df], ignore_index=True)

        # Write to final csv file
        print(self.output_df)
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
            except (AttributeError, ValueError):
                # Not a float, leave alone
                continue

# # === FILE PATHS ===
# transaction_file = "Transaction List.xlsx"
# deposit_file = "DepositReport.xlsx"
# output_cleaned_file = "Cleaned_Transaction_List.xlsx"
# output_journal_file = "Vagaro_Journal_Entry.csv"

# # TODO:
# # Translate Chat GPT's shitty procedural code into method/functions
# # Read from args file to load from default /data directory

# # === STEP 1: READ FILES ===
# trans_df = pd.read_excel(transaction_file, header=None)
# dep_df = pd.read_excel(deposit_file)

# # === STEP 1: Remove first 22 rows and use row 23 as header ===
# trans_df = pd.read_excel(transaction_file, header=22)

# # === STEP 2: Keep only necessary columns and reorder ===
# columns_to_keep = [
#     'Checkout Date', 'Customer', 'Transaction ID', 'Transaction Type',
#     'GiftCertificate No', 'Price', 'Tip', 'Amt paid', 'Disc', 'GC redeem'
# ]
# trans_df = trans_df[columns_to_keep]

# # === STEP 3: Delete rows where all numeric columns sum to 0 ===
# numeric_cols = ['Price', 'Tip', 'Amt paid', 'Disc', 'GC redeem']
# trans_df = trans_df[~(trans_df[numeric_cols].fillna(0).sum(axis=1) == 0)]

# # === STEP 4: Delete last summary row if present ===
# if trans_df.tail(1)[numeric_cols].fillna(0).sum(axis=1).iloc[0] == 0:
#     trans_df = trans_df.iloc[:-1]

# # === STEP 5: Highlight Transaction ID matches from deposit report ===
# matched_ids = dep_df['TranNum'].astype(str).str.strip().tolist()
# trans_df['Highlight'] = trans_df['Transaction ID'].astype(str).str.strip().isin(matched_ids)

# # === STEP 5.1: Highlight refunds if customer matches a deposit report name ===
# deposit_names = dep_df['Name'].str.replace(" ", "", regex=False).str.lower()
# for idx, row in trans_df.iterrows():
#     if str(row['Transaction Type']).lower() == 'refund':
#         customer_name = str(row['Customer']).replace(" ", "").lower()
#         if any(customer_name == name for name in deposit_names):
#             trans_df.at[idx, 'Highlight'] = True

# # === STEP 6: Highlight discounted rows between highlighted rows ===
# trans_df['Discounted'] = (trans_df['Price'].fillna(0)
#                           + trans_df['Tip'].fillna(0)
#                           - trans_df['Amt paid'].fillna(0)) > 0

# highlight_indices = trans_df.index[trans_df['Highlight']].tolist()
# if highlight_indices:
#     min_idx, max_idx = min(highlight_indices), max(highlight_indices)
#     for idx in range(min_idx, max_idx+1):
#         if trans_df.at[idx, 'Discounted']:
#             trans_df.at[idx, 'Highlight'] = True

# # === STEP 7: Highlight discounted row immediately before first match (ghost discount) ===
# chronological_df = trans_df.sort_values(by='Checkout Date')
# first_match_date = chronological_df[chronological_df['Highlight']]['Checkout Date'].min()
# potential_ghosts = chronological_df[chronological_df['Checkout Date'] < first_match_date]
# if not potential_ghosts.empty:
#     last_before = potential_ghosts.iloc[-1]
#     discount = last_before['Price'] - (last_before['Amt paid'] - last_before['Tip'])
#     if discount > 0 and last_before['Amt paid'] == 0:
#         trans_df.loc[last_before.name, 'Highlight'] = True

# # === STEP 8: Header highlight (handled logically, not needed in DataFrame) ===

# # === STEP 9: Delete all non-highlighted rows ===
# trans_df = trans_df[trans_df['Highlight']].copy()

# # === STEP 10: Calculate Disc using formula ===
# trans_df['Disc'] = (trans_df['Price'].fillna(0)
#                     - (trans_df['Amt paid'].fillna(0) - trans_df['Tip'].fillna(0)))
# trans_df.loc[trans_df['Disc'] < 0, 'Disc'] = 0  # Prevent negatives

# # === STEP 11 & 12: Membership handling ===
# if 'Membership' not in trans_df.columns:
#     trans_df.insert(trans_df.columns.get_loc('Disc'), 'Membership', np.nan)

# trans_df.loc[trans_df['Transaction Type'] == 'Membership', 'Membership'] = trans_df['Price']

# # Save cleaned transaction list
# trans_df.to_excel(output_cleaned_file, index=False)

# # === JOURNAL ENTRY CREATION ===
# # Step 13: Bank deposit total
# dep_df['NetAmount'] = dep_df['NetAmount'].replace('[\$,]', '', regex=True).astype(float)
# bank_total = dep_df.loc[~dep_df['TranType'].str.contains('-FANF Fee', case=False, na=False), 'NetAmount'].sum()

# # Step 14: Vagaro Fees (all fees including FANF, Mastercard Location, Chargeback)
# fee_keywords = ['fee', 'chargeback', 'mastercard']
# vagaro_fees = dep_df.loc[dep_df['TranType'].str.lower().str.contains('|'.join(fee_keywords)), 'NetAmount'].abs().sum()

# # Step 15: Massage Income (excluding Memberships and Gift Card Liabilities)
# massage_income = trans_df.loc[~trans_df['Transaction Type'].isin(['Membership','Gift Cards']), 'Price'].sum()

# # Step 16: Tips
# tips_income = trans_df['Tip'].sum()

# # Step 17: Discount Income (debit)
# discount_income = trans_df['Disc'].sum()

# # Step 18: Membership Income
# membership_income = trans_df['Membership'].sum(skipna=True)

# # Step 19: Gift Card Liability
# gift_card_liability = trans_df.loc[trans_df['Transaction Type'] == 'Gift Cards', 'Price'].sum()

# # Step 20: Gift Card Redemptions
# gift_card_redemptions = trans_df.loc[trans_df['GiftCertificate No'].notna(), ['Customer','GC redeem']].dropna()
# redemption_total = gift_card_redemptions['GC redeem'].sum()

# # Adjust Massage Income to subtract gift card redemptions
# massage_income_adj = massage_income - redemption_total

# # Build journal entry
# journal_data = [
#     ["Vagaro", "01-017 Vagaro Fees", "", vagaro_fees],
#     ["Massage Therapy Customers", "02-003 Massage Income", massage_income_adj, ""],
#     ["Massage Therapy Customers", "02-004 Tips for Service Income", tips_income, ""],
#     ["Massage Therapy Customers", "02-008 Membership Income", membership_income, ""],
#     ["Massage Therapy Customers", "02-010 Discount Income", discount_income, ""],
#     ["Massage Therapy Customers", "05-003 Gift Card Liability", gift_card_liability, ""]
# ]

# # Add gift card redemption lines
# for _, row in gift_card_redemptions.iterrows():
#     journal_data.append([
#         row['Customer'],
#         "02-003 Massage Income",
#         row['GC redeem'],
#         ""
#     ])

# journal_df = pd.DataFrame(journal_data, columns=['Received From','Account','Debit','Credit'])
# journal_df.to_csv(output_journal_file, index=False)
# print("Cleanup and journal entry complete!")