import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--output-file", type=str, help="File name for ouput from importing data. Default is output.csv", default="output.csv")
parser.add_argument("--file-path", type=str, help="Path to the file to load data from. Default is ../data/", default="../data/")
parser.add_argument("--date", type=int, help="Date you want to use for running the generator script (in yyyymmddformat) Default is 20240101", default=20240101)
parser.add_argument("--accounts", type=str,
                    help="Accounts required in the journal entry. Default is 02-002 Sales:Food and Beverage Sales, 02-004 Tip Income, 01-031 Delivery App Fees and Commissions:ChowNow fees and commissions, 02-007 Customer Refunds, 07-011 Taxes Payable:Sales and Restaurant Tax Payable",
                    default="02-002 Sales:Food and Beverage Sales, 02-004 Tip Income, 01-031 Delivery App Fees and Commissions:ChowNow fees and commissions, 02-007 Customer Refunds, 07-011 Taxes Payable:Sales and Restaurant Tax Payable")
parser.add_argument("--journal-keys", type=str,
                    help="Keys to include in a journal entry row. Default is Journal Date, Journal Number, Memo, Account, Debits, Credits",
                    default="Journal Date, Journal Number, Memo, Account, Debits, Credits")
parser.add_argument("--is-chow-now", action="store_true", help="Indicates this run should process the chow now import job")
parser.add_argument("--import-journal", action="store_true", help="Indicates this run should process the generic data importer job")
args, unknown_args = parser.parse_known_args()