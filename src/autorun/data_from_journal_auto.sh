#!/bin/bash
cd ..
# FIXME: Date argument must be updated
echo "Generating files..."
if [[ -z $1 ]];
then
echo "Error: Date was not provided and is required"
else
python3.10 __init__.py --date=$1 --import-journal --journal-keys="Journal No.,Journal Date,Received From,Account Name,Description,Payment Method,Ref No,Debits,Credits"
fi
echo "Done!"