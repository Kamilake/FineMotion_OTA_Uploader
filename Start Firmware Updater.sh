!#/bin/bash
# This script will start the firmware updater

python ./update.py
if [ $? -eq 0 ]; then
    echo "Firmware update successful"
    exit 0
else
    python3 ./update.py
fi