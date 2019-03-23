#!/bin/bash

cp /twongo_files/STATUS /root/host_interface/STATUS

while true;
    
    LATEST_HARVEST=`ls -ls /root/host_interface/output/csv | tail -1 | awk '{print $NF}' | sed 's/.csv//'`
    TWONGO_STATUS="Twongo is currently harvesting.";
    sed -i "1s/.*/$TWONGO_STATUS/" /root/host_interface/STATUS;
    sed -i "2s/.*/The most recent harvest was $TWONGO_STATUS/" /root/host_interface/STATUS;
    do /usr/bin/python3 /twongo_files/twongo.py --refresh --log;
    TWONGO_STATUS="Twongo is currently idle.";
    sed -i "1s/.*/$TWONGO_STATUS/" /root/host_interface/STATUS;
    sed -i "2s/.*/The most recent harvest was $TWONGO_STATUS/" /root/host_interface/STATUS;

    sleep 3600;
    
    done;
