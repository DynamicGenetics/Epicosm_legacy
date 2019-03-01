# twongo

A Python3 tweet harvester integrated with MongoDB data management.
This harvester is the python code running in the docker container (URL to be confirmed).

To run, Twitter API credentials will need to be supplied,
by modifying the file "credentials" (instructions inside file).

To run independent of its docker container, the following Python3 dependencies are required:
chardet
idna
oauthlib
pip
psutil
pymongo
PySocks
requests
requests-oauthlib
tweepy  

You will also need a local install of MongoDB version 4 or higher.
The script will try to start MongoDB if it is not running.



