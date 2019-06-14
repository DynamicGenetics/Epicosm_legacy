# twongo

##### A social media harvester integrated with MongoDB for data management.

## Instructions in a nutshell
#### 1. Install Docker.
#### 2. Put these three files into a folder:
  * Twongo_Docker_Launcher (provided here),
  * Twitter credentials file (provided here, but complete with your own Twitter access keys),  
  * and your user_list (supplied by you: one screen name per line, plain text file).
#### 3. Run Twongo_Docker_Launcher by double clicking it, or run it in your terminal/command line.

## Contents
#### 0.1 What does it do?  
#### 1.1 Running with Docker
#### 1.2 Output and other data
#### 2.1 Running the python script independent of docker
#### 2.2 Output and data
#### 2.3 Optional parameters

### 0.1 What does it do?
Twongo is a Twitter harvester. You provide it with a list of users, and it will gather and store all tweets and metadata (going back a maximum of 3240 tweets) for each user. Images, videos and other attachments are stored as URLs. All information is stored by MongoDB. Harvesting can be iterated, for example once a week it can gather new tweets and add them to the database. As well as the full database, output includes a comma-separated-values (.csv) file, with the default fields being the user id number, the tweet id number, time and date, and the tweet content.

Twongo runs in a Docker "container" - this is similar to a virtual machine, where a computer simulates another computer, usually with a different operating system, within itself. Data is sent back onto the main "host" computer for the user to access. This approach means users do not need to install anything other than Docker, running the program is consistent for all users, and use of the program is simplified, requiring little or no command-line experience.


### 1.1 Running with Docker

Twongo's software requirement is [Docker](https://docs.docker.com/install/). Please look up the most up-to-date way of installing for your operating system. At time of writing, running Docker in Windows 10+ requires emulation of a Linux OS, so please follow guides for that.

To run within a docker container, save the file `Twongo_Docker_Launcher` and place it in a folder. Docker must be running: if it is not, it can be started with `systemctl start docker` (on Linux distributions), or `open /Applications/Docker.app` (on MacOS, although it can be started by clicking the app icon).

You must provide 2 further files in the folder with `Twongo_Docker_Launcher`:
1. a list of user screen names in a file called `user_list`.\
The user list must be a plain text file, with a single username (twitter screen name) per line.
2. Twitter API credentials. Please see the file in this repository for a template of this file.\
This file must be called `credentials.py`. You will need your own Twitter API credentials by having a developer account authorised by Twitter. Please see [Twitter documentation](developer.twitter.com/en/apply-for-access.html) for how to do this. Be aware that file names are case sensitive.

Once these three files are ready, `Twongo_Docker_Launcher` can be run by double clicking it, (you might need to provide permission), or it can be run on the command line: `./Twongo_Docker_Launcher` and you will be guided through the process. Once complete, a docker container will be permanently running, and the status of this can be seen using the command.`docker ps`. Your container will stop if docker is ended, or the computer running docker is shutdown or rebooted.\
If stopped, to restart your container, go to the folder with your files in, and run `./Twongo_Docker_Launcher` again, which will recognise that it is in a folder in which it has previously run.

### 1.2 Output and data
Full content and metadata of all tweets is stored in MongoDB, in a database `twitter_db`, with two collections `tweets` which contains all json data and content of each tweet, and "following" which contains a list of all users that each user in your list are following. *MongoDB does not need to be installed on your computer*, all database activity happens in the container.
The following collection will only be made if you ask for following lists to be gathered. *Currently, gathering following list causes the process to be heavily rate limited by Twitter!*

A refined CSV file is created, in the folder `./output/csv/`, which by default collects the user, the\
time of tweet, and the tweet content.

A backup of the entire database is stored in `./output/twitter_db/`. If you have MongoDB installed,\
this can be restored with the command\
`mongorestore [your name given to the database] [the path to the mongodump file]`\
for example:\
`mongoresotore -d twitter_db ./output/twitter_db/tweets`
(However, please check [MongoDB documentation](https://docs.mongodb.com/manual/) as commands can change)\
To view and interact with the database using a GUI, you will need MongoDB installed, and\
a 3rd-party piece of software. Of free options, we find that [Robo 3T](https://robomongo.org/) works well.

### 2.1 Running the python script independent of Docker
This repository is the python code running in the docker container (URL to be confirmed).\
The python3 script will also run independent of its docker container:\
`python3 twongo.py`

You must provide 2 files:
1. a list of user screen names in a file called `user_list`.\
The user list must be a plain text file, with a single username (twitter screen name) per line.
2. Twitter API credentials will need to be supplied, by editing the file "credentials"\
(further instructions inside file, `credentials.py`). You will need your own Twitter API\
credentials by having a developer account authorised by Twitter, and generating\
the required codes. Please see Twitter documentation for how to do this.

Please also see these further requirements.\
1: Put all repository files and your user list into their own folder, and the script will try\
to work out the paths for itself. The python script must be run from the folder it is in.

2: MongoDB version 4 or higher will need to be installed. It does not need to be running,\
the script will check MongoDB's status, and start it if it is not running.\
The working database will be stored in the folder where you place your local copy\
of this repository (not the default location of /data/db). When running with Docker,\
MongoDB is not required because it is included inside the Docker container.\
For Linux and MacOS, use your package manager (eg. apt, yum, yast), for example:\
`apt install mongodb`

3: The following Python3 dependencies will need to be installed, and are most easily done with pip:\
`apt install python3-pip` ("apt" is a common app manager, though it may be brew, yum or others)\
`pip3 install psutil`\
`pip3 install tweepy`\
`pip3 install pymongo`

### 2.2 Output and other data**  
Full content and metadata of all tweets is be stored in MongoDB, in a database "twitter_db",\
with two collections "tweets" which contains all json data and content of each tweet, and\
"following" which contains a list of all users that each user in your list are following.

A refined CSV file is created, in the folder "./output/csv/", which by default collects the user, the\
time of tweet, and the tweet content.

A backup of the entire database is stored in "./output/twitter_db/".\
This can be restored by MongoDB using the command\
`mongorestore [your name given to the database] [the path to the mongodump file]`\
for example:\
`mongorestore -d twitter_db ./output/twitter_db/tweets`\
(However, please check MongoDB documentation as commands can change)

### 2.3 Optional parameters  
The following can be added to your command:\
`--log`           Create a logfile of all output from the harvest run, in /twongo_logs\
`--refresh`       Refresh the user list (if you want to modify the list of users to harvest\
                    from, replace your file "user_list", and run with -r so that this is refreshed)\
`--getfriends`    Gather friend list. This list will go into the MongoDB collection "friends",\
                    in the database "twitter_db". This is normally disabled because requesting the\
                    friend list can be very demanding on the API and the run will be severely rate limited.
