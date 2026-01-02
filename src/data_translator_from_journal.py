# This file loads in data from a journal entry and translates it into the needed csv output file format

import pandas as pd
import numpy as np
import logging
import os
import copy

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

        # Lastly, check if there are any discounts applied in the file
        # if (transaction_df['Apply Discount'] == 'yes').any():
        #     has_discounts_applied = True
        # else:
        #     has_discounts_applied = False

        for index, entry in transaction_df.iterrows():
            # Each row may have profit and fee information associated with it
            # The code at the end ensures these are separate row numbers on the final csv
            if has_single_debit is False:
                data_row_factory = DataRowFactory()

            # Match the transaction ids between the 2 dataframes
            transaction_number = entry['Transaction ID']
            transaction_row = deposit_df.loc[deposit_df['TranNum'] == transaction_number]

            if transaction_row.empty:
                # FIXME: This may not be right. I'm assuming some logic applies where a profit must be counted even if no fees
                # That profit row must, however, be greater than 0 or the row is skipped
                if entry['Transaction Type'] == 'Membership' and has_single_debit is False:
                    credits = entry['Qty'] * entry['Price']
                    if credits > 0:
                        profit_row = data_row_factory.build_data_row('membership')
                        profit_row["Credits"] = credits

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

                    # Discounts applied as their own row
                    if 'discounts_row' in locals() and 'Debits' in discounts_row:
                        discounts_row["Debits"] = float(str(discounts_row['Debits']).replace('$', '')) + entry['Disc']
                    elif entry['Disc']:
                        discounts_row = data_row_factory.build_data_row('discount')
                        discounts_row["Debits"] = entry['Disc']
                    print('got profit_row:', profit_row)

                elif entry['Transaction Type'] == 'Membership':
                    # We'll use a raw_profit of 0 to cover cases where there is no profit in this transaction
                    raw_profit = 0
                    profit_row = data_row_factory.build_data_row('membership')

                    # Convert the profit amount back to currency (.00 on whole values)
                    raw_profit = entry['Qty'] * entry['Price']
                    if profit_row["Credits"]:
                        raw_profit += profit_row["Credits"]
                    if raw_profit > 0:
                        profit_amount = f"${str(raw_profit)}"
                        if '.' not in profit_amount:
                            profit_amount += '.00'
                        profit_row["Credits"] = profit_amount

                # If we totaled the debits, then don't write again
                if has_single_debit:
                    write_debits = False
                else:
                    # Build the totals row to append
                    total_amount = raw_profit + raw_debit # We sum here because the value in debits is stored as negative
                    if total_amount > 0 or write_debits is True:
                        totals_row = data_row_factory.build_data_row('')

                        # NOTE: These are inverted because that's how banks handle debits/credits
                        if total_amount < 0:
                            totals_row["Credits"] = total_amount
                        else:
                            totals_row["Debits"] = total_amount

            # If we have just a single debit, aggregate sum the values rather than splitting
            if has_single_debit and index < len(transaction_df) -1:
                continue

            # Add new row containing every record we got on this pass
            data_types = [str(x) for x in data_row_factory.data_types]
            data_set = []
            for data_type in data_types:
                if data_type == 'vagaro':
                    data_set.append(fee_row)
                elif data_type == 'income' or data_type == 'membership':
                    data_set.append(profit_row)
                elif data_type == 'tips':
                    data_set.append(tips_row)
                elif data_type == 'discount':
                    data_set.append(discounts_row)
                else:
                    data_set.append(totals_row)

            # if tips_row:
            #     data_set = [fee_row, profit_row, tips_row, totals_row]
            # else:
            #     data_set = [fee_row, profit_row, totals_row]
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
            except (AttributeError, ValueError, TypeError):
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