# twongo

=== A Python3 tweet harvester integrated with MongoDB data management ===

This harvester is the python code running in the docker container (URL to be confirmed).
It will also run independent of its docker container, with these prerequisites:

1: Put all repo files into their own folder, and the script will try to work out the paths for itself.
The python script must be run from the folder it is in.

2: Twitter API credentials will need to be supplied, by editing the file "credentials"
(further instructions inside file, "credentials"). You will need to acquire these
credentials by having a developer account authorised by Twitter and generating
the required codes.

3: MongoDB version 4 or higher will need to be installed. It does not need to be running,
the script will ascertain MongoDB's status, and start it if it is not running.

4: The following Python3 dependencies will need to be installed:
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
