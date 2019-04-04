#!/bin/bash
## Docker container starter for twongo.py, Al Tanner, April 2019
## For full details see https://github.com/DynamicGenetics/twongo

echo "_.~^~._.~^~._.~  twongo docker container runner  ~._.~^~._.~^~._.~^";
echo "Please have your credentials file and user_list in this run folder.";

## Ask user how often to harvest.
read -p "How often would you like to harvest (in hours)? " frequency;
while ! [[ "$frequency" =~ ^[0-9]+$ ]]; do
    read -p "Please enter a valid number of hours between harvests: " frequency;
done;

## Look for a previous run - user may want to refresh their list of users.
if [ -f $PWD/STATUS ]; then
    echo "It looks like twongo has run in this folder previously.";
    read -p "Do you want to refresh your user_list? (y/n): " refresh_reply;
    while ! [[ "$refresh_reply" =~ ^[yn]$ ]]; do
        read -p "(y/n): " refresh_reply;
    done;    
fi

## Ask user if they want to log things to a file.
read -p "Do you want to create a log file (y/n): " log_reply;
while ! [[ "$log_reply" =~ ^[yn]$ ]]; do
    read -p "(y/n): " log_reply;
done;    

## Set up variables based on user responses.
if [[ $log_reply = "y" ]]; then
    log=--log;
fi
if [[ $refresh_reply = "y" ]]; then
    refresh=--refresh;
fi

## How long between harvest in seconds.
frequency_in_seconds=$(($frequency*3600))

echo "OK, twongo starting, harvesting once every $frequency hours.";
secs=5

## Give users a chance to cancel...
while [ $secs -gt 0 ]; do
   echo -ne "Starting in $secs\033[0K\r"
   sleep 1
   : $((secs--))
done

## If refreshing, do one refresh iteration, then loop into not refreshing like normal.
if [[ $refresh_reply = "y" ]]; then
    docker run -d -v $PWD:/root/host_interface/ altanner/twongo:latest /bin/bash -c "/usr/bin/python3 /twongo/twongo.py $refresh $log; sleep $frequency_in_seconds; while true; do /usr/bin/python3 /twongo/twongo.py $log; sleep $frequency_in_seconds; done";
else

## If not refreshing, just harvest and wait.
docker run -d -v $PWD:/root/host_interface/ altanner/twongo:latest /bin/bash -c "while true; do /usr/bin/python3 /twongo/twongo.py $refresh $log; sleep $frequency_in_seconds; done";
fi

## I guess I could send this to devnull, but there might be important output here on error...
echo "(That's a hash from Docker, you can ignore it...) just a moment";

## Give docker a moment to set things up.
waiting=6
while [ $waiting -gt 0 ]; do
    echo -ne "_";sleep 0.05;echo -ne ".";sleep 0.2;echo -ne "~";sleep 0.2;
    echo -ne "^";sleep 0.03;echo -ne "~";sleep 0.1;echo -ne ".";sleep 0.05;
    : $((waiting--))
done

## Report that things are up. Docker should error above if things went wrong.
container_name=`docker ps | sed -n 2p | awk 'END {print $NF}'`;
printf "\nOK, container launched, Docker assigned your container the name \"$container_name\"\n";
echo "To end this process, run this command: docker stop $container_name";
