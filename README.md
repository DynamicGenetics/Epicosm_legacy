# twongo

=== A Python3 tweet harvester integrated with MongoDB data management ===

This repository is the python code running in the docker container (URL to be confirmed).
It will also run independent of its docker container, with these prerequisites:

1: Put all repository files into their own folder, and the script will try to work out the paths for itself.
The python script must be run from the folder it is in.

2: Twitter API credentials will need to be supplied, by editing the file "credentials"
(further instructions inside file, "credentials"). You will need your own API
credentials by having a developer account authorised by Twitter and generating
the required codes. Please see Twitter documentation for how to do this.

3: MongoDB version 4 or higher will need to be installed. It does not need to be running,
the script will ascertain MongoDB's status, and start it if it is not running.
The working database will be stored in the folder where you place your local copy
of this repository (not the default location of /data/db).  
For Linux and MacOS, use your package manager (eg. apt, yum, yast), for example:  
apt install mongodb  

4: The following Python3 dependencies will need to be installed, and are most easily done with pip:  
apt install python3-pip  
pip3 install psutil  
pip3 install tweepy  
pip3 install pymongo  

5: The script is then run as follows  
python3 twongo.py [your list of user names]  
for example  
python3 twongo.py 200_users

=== Output and data ===
Full metadata of all tweets is be stored in MongoDB, in a database "twitter_db", with two collections  
"tweets" which contains all json data and content of each tweet, and  
"following" which contains a list of all users that each user in your list are following.  
A refined CSV file is created, in the folder "./output/csv/", which at the moment collects the user, the  
time of tweet, and the tweet content.  
A backup of the entire database is stored in "./output/twitter_db/". This can be restored by MongoDB using  
the command "mongorestore [your name given to the database] [the path to the mongodump file]  
for example:  
mongoresotore twitter_db ./output/twitter_db/tweets  
(However, please check MongoDB documentation as commands sometimes change)  
