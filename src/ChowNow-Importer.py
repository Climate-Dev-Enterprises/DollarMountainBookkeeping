import pandas as pd
from args import args

# === CONFIGURATION ===
file_path = "DisbursementReport_16Jul25_to_27Jul25.xls"  # <-- update if needed
output_file = "ChowNow_JE_Output.csv"

# === Load spreadsheet ===
try:
    df = pd.read_excel(file_path, engine='xlrd')
except:
    df = pd.read_excel(file_path, engine='openpyxl')

# === Inspect columns (for debugging, optional) ===
print("🧾 Available columns:", df.columns.tolist())

# === Filter summary rows (gray rows only) ===
summary_rows = df[df["Daily Total"].notna()]
print(f"\n📊 Found {len(summary_rows)} summary (deposit) rows.")

journal_entries = []

# === Helper: create a clean row ===
def build_je_row(date, number, memo, account, debit=0, credit=0):
    if not debit and not credit:
        return None
    return {
        "Journal Date": date,
        "Journal Number": number,
        "Memo": memo,
        "Account": account,
        "Debits": round(debit, 2) if debit else "",
        "Credits": round(credit, 2) if credit else ""
    }

# === Build journal entries ===
for _, row in summary_rows.iterrows():
    disb_date_raw = row.get("Disbursement Date")
    if pd.isna(disb_date_raw):
        print("⚠️ Skipping row with missing Disbursement Date.")
        continue

    try:
        date = pd.to_datetime(disb_date_raw).strftime("%m/%d/%Y")
        je_num = f"CN - Dep - {date[:-5]}"
        memo = f"ChowNow Deposit {date}"
    except Exception as e:
        print(f"❌ Skipping row with bad date format: {disb_date_raw} ({e})")
        continue

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

    rows_to_add = [
        build_je_row(date, je_num, memo, "02-002 Sales:Food and Beverage Sales", credit=sales_credit),
        build_je_row(date, je_num, memo, "02-004 Tip Income", credit=tip),
        build_je_row(date, je_num, memo, "01-031 Delivery App Fees and Commissions:ChowNow fees and commissions", credit=fees),
        build_je_row(date, je_num, memo, "02-007 Customer Refunds", credit=refunds),
        build_je_row(date, je_num, memo, "07-011 Taxes Payable:Sales and Restaurant Tax Payable", credit=tax),
    ]

    if discount > 0:
        rows_to_add.append(build_je_row(date, je_num, memo, "02-006 Discount Income", debit=discount))

    rows_to_add.append(build_je_row(date, je_num, memo, "00-001 BUSINESS CHECKING (0050) - 1", debit=daily_total))

    # Add only valid rows
    for r in rows_to_add:
        if r:
            journal_entries.append(r)

# === Save to CSV ===
pd.DataFrame(journal_entries).to_csv(output_file, index=False)
print(f"\n✅ Finished! Journal entries saved to: {output_file}")
