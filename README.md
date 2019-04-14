# twongo

**=== A Python3 tweet harvester integrated with MongoDB data management ===**  
**=== Alastair Tanner, February 2019 ===**  
**=== MRC Integrative Epidemiology Unit, University of Bristol, UK ===**

**tl;dr:** put [1] Twongo_Docker_Launcher, [2] Twitter credentials file, and [3] user_list into a folder  
and run Twongo_Docker_Launcher by double clicking it, or run it on the command line.  

**Contents.**  
1.1 Running with docker.  
1.2 Output and other data.  
2.1 Running the python script independent of docker.  
2.2 Output and data.  
2.3 Optional parameters.  

**1.1 == Running with docker ==**

To run within a docker container, save the file "Twongo_Docker_Launcher" and place it in a folder.

You must provide 2 further files in the folder with Twongo_Docker_Launcher:  
1. a list of user screen names in a file called "user_list".  
The user list must be a plain text file, with a single username (twitter screen name) per line.  
2. Twitter API credentials. Please see the file in this repository for a template of this file.  
This file must be called "credentials". You will need your own Twitter API credentials by having  
a developer account authorised by Twitter.  
Please see Twitter documentation for how to do this.  
Be aware that file names are case sensitive.  

Once these three files are ready, Twongo_Docker_Launcher can be run by double clicking it,  
(you might need to provide permission), or it can be run on the command line:  
./Twongo\ Docker\ Launcher  
and you will be guided through the process. Once complete, a docker container will be 
permanently running, and the status of this can be seen using the command. 
docker ps  
Your container will stop if docker is ended, or the computer running docker is shutdown or rebooted.
If stopped, to restart your container, go to the folder with your files in, and execute Twongo_Docker_Launcher  
again, which will recognise that it is in a folder in which it has previously run.

**1.2 == Output and data ==**  
Full content and metadata of all tweets is be stored in MongoDB, in a database "twitter_db",  
with two collections "tweets" which contains all json data and content of each tweet, and  
"following" which contains a list of all users that each user in your list are following.  
The following collection will only be made if you ask for following lists to be gathered.  
**Currently, gathering following list causes the process to be heavily rate limited by Twitter!**  

A refined CSV file is created, in the folder "./output/csv/", which by default collects the user, the  
time of tweet, and the tweet content.  

A backup of the entire database is stored in "./output/twitter_db/". This can be restored by MongoDB using  
the command "mongorestore [your name given to the database] [the path to the mongodump file]"  
for example:  
mongoresotore -d twitter_db ./output/twitter_db/tweets  
(However, please check MongoDB documentation as commands can change) 



**2.1 == Running the python script independent of docker ==**  
This repository is the python code running in the docker container (URL to be confirmed).
The python script will also run independent of its docker container:  

python twongo.py

You must provide 2 files:  
1. a list of user screen names in a file called "user_list".  
The user list must be a plain text file, with a single username (twitter screen name) per line.  
2. Twitter API credentials will need to be supplied, by editing the file "credentials"
(further instructions inside file, "credentials"). You will need your own Twitter API
credentials by having a developer account authorised by Twitter, and generating
the required codes. Please see Twitter documentation for how to do this.  

Please also see these further requirements.  

1: Put all repository files and your user list into their own folder, and the script will try  
to work out the paths for itself. The python script must be run from the folder it is in.

2: MongoDB version 4 or higher will need to be installed. It does not need to be running,
the script will check MongoDB's status, and start it if it is not running.
The working database will be stored in the folder where you place your local copy
of this repository (not the default location of /data/db).  
For Linux and MacOS, use your package manager (eg. apt, yum, yast), for example:  
apt install mongodb  

3: The following Python3 dependencies will need to be installed, and are most easily done with pip:  
apt install python3-pip ("apt" is a common app manager, though it may be brew, yum or others)  
pip3 install psutil  
pip3 install tweepy  
pip3 install pymongo  

**2.2 == Output and data ==**  
Full content and metadata of all tweets is be stored in MongoDB, in a database "twitter_db",  
with two collections "tweets" which contains all json data and content of each tweet, and  
"following" which contains a list of all users that each user in your list are following.  

A refined CSV file is created, in the folder "./output/csv/", which by default collects the user, the  
time of tweet, and the tweet content.  

A backup of the entire database is stored in "./output/twitter_db/". This can be restored by MongoDB using  
the command "mongorestore [your name given to the database] [the path to the mongodump file]"  
for example:  
mongoresotore -d twitter_db ./output/twitter_db/tweets  
(However, please check MongoDB documentation as commands can change)  
  
**2.3 == Optional parameters ==**  
The following can be added to your command:  
--log           Create a logfile of all output from the harvest run, in /twongo_logs  
--refresh       Refresh the user list (if you want to modify the list of users to harvest  
                from, replace your file "user_list", and run with -r so that this is refreshed)  
--getfriends    Gather friend list. This list will go into the MongoDB collection "friends",  
                in the database "twitter_db". This is normally disabled because requesting the  
                friend list can be very demanding on the API and the run will be severely rate limited.  
