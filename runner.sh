#!/bin/bash
# Docker starter

echo "[o_o] twongo is about to start _.~\"~._.~\"~._.~\"~._.~\"~.__.~\"~._.~\"~";
echo "Please have your credentials file and user_list in this run folder."

read -p "How often would you like to harvest (in hours)? " frequency;
while ! [[ "$frequency" =~ ^[0-9]+$ ]]; do
    read -p "Please enter a valid number of hours between harvests: " frequency;
done;
    
if [ -f $PWD/STATUS ]; then
    echo "It looks like twongo has run in this folder previously.";
    read -p "Do you want to refresh your user_list? (y/n): " refresh_reply;
    while ! [[ "$refresh_reply" =~ ^[YyNn]$ ]]; do
        read -p "(y/n): " refresh_reply;
    done;    
fi

read -p "Do you want to create a log file (y/n): " log_reply;
while ! [[ "$log_reply" =~ ^[YyNn]$ ]]; do
    read -p "(y/n): " log_reply;
done;    

if [[ $log_reply = "y" ]]; then
    log=--log;
fi
if [[ $refresh_reply = "y" ]]; then
    refresh=--refresh;
fi

frequency_in_seconds=$(($frequency*3600))

echo "OK, twongo starting, harvesting once every $frequency hours.";
echo "To stop this process, run this command: docker stop \$(docker ps -a -q) "
echo "(This will stop all running containers, to stop this one specifically, please search for the container id.)"

echo $frequency_in_seconds
echo $refresh
echo $log

docker run -d -v $PWD:/root/host_interface/ altanner/twongo:latest /bin/bash -c "while true; do /usr/bin/python3 /twongo/twongo.py $refresh $log; sleep $frequency_in_seconds; done"
