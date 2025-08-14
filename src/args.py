import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--output-file", type=str, help="File name for ouput from importing data. Default is output.csh", default="output.csv")
args, unknown_args = parser.parse_known_args()