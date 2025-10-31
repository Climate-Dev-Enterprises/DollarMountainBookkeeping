#!/bin/bash
cd ..
if [[ -z $1 ]];
then
python3.10 __init__.py --install
else
python3.10 __init__.py --reinstall
fi