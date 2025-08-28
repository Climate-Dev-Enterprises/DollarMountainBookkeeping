# This file loads in data from a journal entry and translates it into the needed csv output file format

import pandas as pd
import numpy as np
from datetime import datetime

class JournalDataImporter:

    def __init__(self, args):
        pass

    def load_source_data_file(self):
        pass

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