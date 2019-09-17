#!/bin/bash

## Docker container starter for Epicosm
## For full details see https://github.com/DynamicGenetics/Epicosm

if [ `whoami` != root ]; then
    printf "Epicosm must be run as root, or using sudo.\n";
    exit;
fi

## Move to the working directory (needed if run from GUI)
cd -- "$(dirname -- "$BASH_SOURCE")"

## Deal with control-c interrupt
trap ctrl_c INT
function ctrl_c() {
    printf "\nEpicosm aborted by user.\n";
    exit 0;
}

## Check if docker is running on system.
docker images >/dev/null 2>&1;
docker_exit_code=$?;
if [[ $docker_exit_code != 0 ]]; then 
    if ! pgrep -x "docker" > /dev/null; then
        if ! pgrep -x "dockerd" > /dev/null; then
            printf "Docker doesn't appear to be running here.\n";
            printf "Please start Docker and try again. Exiting.\n";
            read -p "(Press enter to close.)";
            exit 1;
        fi
    fi
fi 

## Check if a container is already running using this folder as volume
if [ -f $PWD/.container_name ]; then
    container=`cat .container_name`
    if docker ps | grep -q $container; then
        printf "It looks like the Docker container \"$container\" is currently using this folder.\n";
        printf "You can stop $container with:   docker stop $container    or use a new folder for this run.\n";
        read -p "(Press enter to close.)";
        exit 1;
    fi
fi

## Check if required files are in the working directory.
if [ ! -f $PWD/credentials.py ] || [ ! -f $PWD/user_list ]; then
    printf "Your credentials.py file and/or user_list don't appear to be here.\n";
    printf "Please have your credentials file and user_list in this run folder.\n";
    read -p "(Press enter to close.)";
    exit 1;
fi

## Intro message
printf "\n======================================\n"
printf "= Epicosm: Docker Container Launcher =\n";
printf "=== dockerhub.com/altanner/Epicosm ===\n";
printf "= github.com/DynamicGenetics/Epicosm =\n";
printf "======================================\n";

## If first run, get Docker image from dockerhub.
if ! docker images | grep -q altanner/epicosm; then # this breaks on centos unless the whole script is sudo. adding sudo here doesn't help.
    printf "It looks like your first run on this system.\n";
    printf "Download may take a few minutes, depending on connection speed.\n";
    read -p "Should I continue? (y/n): " download_reply;
    while ! [[ "$download_reply" =~ ^[yn]$ ]]; do
        read -p "(y/n): " download_reply;
    done;  
    if [[ $download_reply = "n" ]]; then
        read -p "OK, stopping. Press enter to close.";
        exit 0;
    fi
fi

## Check for updates and pull if necessary
printf "\nChecking for updates... "
docker pull altanner/epicosm:latest;

## Ask user how often to harvest.
printf "\nInfo: Harvests are typically done every few days. Speed will depend on a range of factors,\n";
printf "but very roughly Epicosm runs at 100 users per hour on first run, and faster on subsequent runs.\n\n"; 
read -p "How often would you like to harvest (in hours)? " frequency;
while ! [[ "$frequency" =~ ^[0-9]+$ ]]; do
    read -p "Please enter a valid number of hours between harvests: " frequency;
done;

## Ask if users want to gather the following list of users.
printf "\nInfo: Gathering users' following lists takes significantly longer than gathering just tweets.\n";
printf "(but this will only affect the first run).\n\n";
read -p "Do you want to gather the following list of each user? (y/n): " following_reply;
while ! [[ "$following_reply" =~ ^[yn]$ ]]; do
    read -p "(y/n): " following_reply;
done;
if [[ $following_reply = "y" ]]; then
    following=--get_following;
fi

## Look for a previous run - ask if user wants to refresh their list of users.
if [ -f $PWD/STATUS ]; then
    printf "\nIt looks like Epicosm has run in this folder previously.\n\n";
    read -p "Do you want to refresh your user_list? (y/n): " refresh_reply;
    while ! [[ "$refresh_reply" =~ ^[yn]$ ]]; do
        read -p "(y/n): " refresh_reply;
    done;    
fi
if [[ $refresh_reply = "y" ]]; then
    refresh=--refresh;
fi

## How long between harvest in seconds.
frequency_in_seconds=$(($frequency*3600));

## How many users does it look like?
number_of_users=$(grep -cve '^\s*$' $PWD/user_list)

## Confirm start
printf "OK, Epicosm starting, harvesting from $number_of_users users, once every $frequency hours.\n";

## Docker run, sending shell command into container with replies to qs
## First iteration refreshing or getting following list, then into a loop just harvesting
docker run -d -v $PWD:/root/host_interface/ altanner/epicosm:latest /bin/bash -c "cp /root/host_interface/credentials.py /Epicosm/credentials.py; /usr/bin/python3 /Epicosm/epicosm.py $refresh $following --log; sleep $frequency_in_seconds; while true; do /usr/bin/python3 /Epicosm/epicosm.py --log; sleep $frequency_in_seconds; done" 1>/dev/null;

## Report that things are up & make some status files. Docker should error above if things went wrong.
container_name=$(docker ps | sed -n 2p | awk 'END {print $NF}');
echo $container_name > $PWD/.container_name;
echo $frequency > $PWD/.frequency
printf "\nDocker assigned your container the name:    $container_name";
printf "\nTo end the process, run this command:       docker stop $container_name";
printf "\nTo see your active containers:              docker ps";
printf "\nCurrent status of your process:             cat STATUS";
printf "\nCSV output files are in:                    /output/csv";
printf "\nFor more information, see log files in:     /epicosm_logs\n\n";

## Outro message.
read -p "Press enter to exit(!) - (your container will continue running)"
printf "\n";
exit 0;

