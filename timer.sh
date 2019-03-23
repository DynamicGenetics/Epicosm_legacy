#!/bin/bash

# periodically runs twongo, and updates current status
# the time duration between runs can be modified by altering
# the sleep time (in seconds), on line 19.

touch /root/host_interface/STATUS;
sed -i '1,2d' /root/host_interface/STATUS;
echo -e '\n' > /root/host_interface/STATUS;

while true;
    
    TWONGO_STATUS="Twongo is currently harvesting.";
    sed -i "1s/.*/$TWONGO_STATUS/" /root/host_interface/STATUS;
    do /usr/bin/python3 /twongo/twongo.py --refresh;
    TWONGO_STATUS="Twongo is currently idle.";
    LATEST_HARVEST=`ls -ls /root/host_interface/output/csv | tail -1 | awk '{print $NF}' | sed 's/.csv//'`;
    sed -i "1s/.*/$TWONGO_STATUS/" /root/host_interface/STATUS;
    sed -i "2s/.*/The most recent harvest was $LATEST_HARVEST/" /root/host_interface/STATUS;

    sleep 3200;
    
    done;
    
