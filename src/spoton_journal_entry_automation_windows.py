# SpotOn Journal Entry Automation Script for QBO Import
import pandas as pd
from datetime import datetime

# Constants
EXCLUDED_NET_VALUES = [-0.25, -0.5, -0.75, -1.0, -1.25, -1.5, -1.75]
TAXABLE_SALES = "04-0000 Taxable Sales"
SPOTON_FEES = "06-0034 General Business Expenses:Merchant account services - SpotOn"
BANK_ACCOUNT = "00-0001 ZIONS Business Inspire Checking (1205)"


def process_spoton_file(file_path, output_csv_path):
    # Step 1: Load and set headers from row 9
    df_raw = pd.read_csv(file_path, header=None)
    new_header = df_raw.iloc[8]
    df = df_raw.iloc[9:].copy()
    df.columns = new_header
    df.reset_index(drop=True, inplace=True)

    # Step 2: Drop unnecessary columns
    cols_to_drop = [
        "Settlement Time", "Activity Date", "Category",
        "Memo", "Description", "Amount"
    ]
    df.drop(columns=[col for col in cols_to_drop if col in df.columns], inplace=True)

    # Step 3: Drop blank rows
    df.dropna(how="all", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Step 4: Add "Journal No" column
    insert_at = df.columns.get_loc("Estimated Deposit Date")
    df.insert(insert_at, "Journal No", "")

    # Step 5: Remove rows with excluded Net Transferred values
    df["Net Transferred"] = pd.to_numeric(df["Net Transferred"], errors="coerce")
    df = df[~df["Net Transferred"].round(2).isin(EXCLUDED_NET_VALUES)].reset_index(drop=True)

    # Step 6: Fill "Journal No" values
    df["Estimated Deposit Date"] = pd.to_datetime(df["Estimated Deposit Date"], errors="coerce")
    df["Journal No"] = [f"{d.strftime('%m/%d')} SpotOn {i+1}" for i, d in enumerate(df["Estimated Deposit Date"])]

    # Step 7: Convert values to numeric
    for col in ["Total Credit Payment", "Fees", "Others"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Step 8 & 9: Build journal entry rows with Payee and export
    journal_entries = []
    for _, row in df.iterrows():
        date_str = row["Estimated Deposit Date"].strftime("%#m/%#d/%Y")
        journal_no = row["Journal No"]

        if pd.notna(row["Total Credit Payment"]) and row["Total Credit Payment"] != 0:
            journal_entries.append({
                "Journal No": journal_no, "Date": date_str, "Account": TAXABLE_SALES,
                "Debits": "", "Credits": row["Total Credit Payment"], "Payee": "SpotOn"
            })
        if pd.notna(row["Fees"]) and row["Fees"] != 0:
            journal_entries.append({
                "Journal No": journal_no, "Date": date_str, "Account": SPOTON_FEES,
                "Debits": abs(row["Fees"]), "Credits": "", "Payee": "SpotOn"
            })
        if pd.notna(row["Others"]) and row["Others"] != 0:
            journal_entries.append({
                "Journal No": journal_no, "Date": date_str, "Account": TAXABLE_SALES,
                "Debits": abs(row["Others"]), "Credits": "", "Payee": "SpotOn"
            })
        if pd.notna(row["Net Transferred"]) and row["Net Transferred"] != 0:
            journal_entries.append({
                "Journal No": journal_no, "Date": date_str, "Account": BANK_ACCOUNT,
                "Debits": row["Net Transferred"], "Credits": "", "Payee": "SpotOn"
            })

    journal_df = pd.DataFrame(journal_entries)
    journal_df.to_csv(output_csv_path, index=False)


# Example usage:
# process_spoton_file("/path/to/input.csv", "/path/to/output.csv")


# Run the script when executed directly
if __name__ == "__main__":
    INPUT_FILE = "Settlements_Report_20250701_20250718.csv"  # Replace with your actual file name if needed
    OUTPUT_FILE = "SpotOn_JE_Output.csv"
    process_spoton_file(INPUT_FILE, OUTPUT_FILE)
    print(f"Journal entry CSV successfully created at: {OUTPUT_FILE}")
