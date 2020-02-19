
<p align="center">
   <a href="https://github.com/DynamicGenetics/Epicosm"><img src="img/epicosmPNGsmall.png" width="300"></a> 
</p>
<p align="center">
   <a href="https://www.python.org/"><img src="img/python_logo.png" width="100" height="80" /></a> 
   <a href="https://www.docker.com/"><img src="img/docker_logo.png" width="100" height="80" /></a> 
   <a href="https://www.mongodb.com/"><img src="img/mongo_logo.png" width="100" height="80" /></a> 
</p>

  [![Build Status](https://travis-ci.com/altanner/Epicosm.svg?token=9HPZTDQLbUBqyFNBytob&branch=master)](https://travis-ci.com/altanner/Epicosm)
  [![GPLv3 license](https://img.shields.io/badge/licence-GPL_v3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
  ![DOI](https://img.shields.io/badge/DOI-TBC-blue.svg)

## Overview
Epicosm: Epidemiology of Cohort Social Media. 
* Harvest ongoing and retrospective Tweets from a list of users.
* Real-time stream-listening from geographic locations.
* [in development] Real-time mapping of sentiment analysis.
* Sentiment analysis of Tweets using labMT, Vader and LIWC (dictionary required for the latter).
* [in development] Benchmarking of sentiment analysis against ground truth validations.



## Instructions in a nutshell
#### 1. [Download the Epicosm repository](https://github.com/DynamicGenetics/Epicosm/archive/master.zip)
#### 2. Install [MongoDB](https://www.mongodb.com/):
  * In a Mac terminal type `brew install mongodb`
  * In a Linux terminal type `apt install mongodb`
#### 3. Put these three files into a folder:
  * `epicosm_mac` OR `epicosm_linux`, depending on your operating system,
  * `credentials.txt` file (provided here, but complete with [your own Twitter access keys](https://github.com/DynamicGenetics/Epicosm/blob/master/Twitter_Authorisation.pdf)),  
  * and your `user_list` (supplied by you: one screen name per line, plain text file).

#### 4. Double click or run Epicosm: 
`./epicosm_linux` or `./epicosm_mac`

#### (5. Alternatively, you can run `python epicosm.py` in /src, but you will have to update your own dependencies for it to run successfully; follow instructions in section 2.1.)
<p align="center"> ••• </p>

## Documentation
#### 0.1 What does it do?  
#### 1.1 Running Epicosm
#### 1.2 Output and other data
#### 2.1 Running python scripts
#### 2.2 Optional parameters
#### 3.0 License

<p align="center"> ••• </p>

### 0.1 What does it do?
Epicosm is a social media harvester and sentiment analyser. Currently, the platform uses Twitter as the data source and LIWC as the sentiment analysis method. You provide it with a list of users, and it will gather and store all tweets and metadata (going back a maximum of 3240 tweets) for each user. Images, videos and other attachments are stored as URLs. All information is stored by MongoDB. Harvesting can be iterated, for example once a week it can gather new tweets and add them to the database. As well as the full database, output includes a comma-separated-values (.csv) file, with the default fields being the user id number, the tweet id number, time and date, and the tweet content.

Epicosm uses [MongoDB](https://www.mongodb.com/) for data management, and this must be installed before being running Epicosm. This can be done through downloading and installing from the MongoDB website, or it can be done in a Terminal window with the commands
`brew install mongodb` on a Mac
`apt install mongodb` on Linux (Debian-based systems like Ubuntu).

Epicosm can be run in two ways. It can be run using the executables provided, `epicosm_mac` or `epicosm_linux`. If there are any issues with your input files (your `user_list` and your `credentials.txt`) Epicosm will try to help you. Alternatively, Epicosm can be run by Python version 3+; details are in section 2.1.

You will need Twitter API credentials by having a developer account authorised by Twitter. Please see our [guide to getting an authorised account](https://github.com/DynamicGenetics/Epicosm/blob/master/Twitter_Authorisation.pdf), and there are further details on [Twitter documentation](developer.twitter.com/en/apply-for-access.html) for how to do this.

<p align="center"> ••• </p>

### 1.1 Running Epicosm from executable

This is the usual way of running Epicosm (see section 2.1 for running using Python).

You must provide 2 further files in the folder with the Epicosm executable:
1. a list of user screen names in a file called `user_list`. The user list must be a plain text file, with a single username (twitter screen name) per line.
2. Twitter API credentials. Please see the file in this repository for a template. This file must be called `credentials.py`.

Then you can run the suitable executable,
`./epicosm_linux` or
`./epicosm_mac`

<p align="center"> ••• </p>

### 1.2 Output and data
The processed output is a a database of tweets from the users in your `user_list`, and a CSV file, in the folder `./output/csv/`, which by default has the fields: [1] the ID of the tweeter, [2] the id of the tweet, [3] the time and date of the tweet, and [4] the tweet content.

A log file detailing what Epicosm has done is in `/epicosm_logs/`.

Full tweet content and metadata of all tweets is stored in [MongoDB](https://www.mongodb.com/) in json format. To work with full raw data, you will need MongoDB installed. The tweet database is named `twitter_db`, with two collections `tweets`, and `following` which contains a list of all users that each user in your list are following. The `following` collection will only be made if you ask for following lists to be gathered. *Currently, gathering following list causes the process to be heavily rate limited by Twitter! [solution in progress]*

A backup of the entire database is stored in `/output/twitter_db/`. If you have MongoDB installed, this can be restored with the command

`mongorestore [your name given to the database] [the path to the mongodump bson file]`

for example:

`mongoresotore -d twitter_db ./output/twitter_db/tweets.bson`

(However, please check [MongoDB documentation](https://docs.mongodb.com/manual/) as commands can change)

To view and interact with the database using a GUI, you will need MongoDB installed, and a database viewer. Of open source options, we find that [Robo 3T](https://robomongo.org/) works very well.

<p align="center"> ••• </p>

### 2.1 Running the python script manually
See the source file in `/src` and run it with

`python3 epicosm.py`

You must provide 2 files:
1. a list of user screen names in a file called `user_list`. The user list must be a plain text file, with a single username (twitter screen name) per line.  
2. Twitter API credentials will need to be supplied, by editing the file `credentials.py` (further instructions inside file). You will need your own Twitter API credentials by having a developer account authorised by Twitter, and generating the required codes. Please see [our guide](https://github.com/DynamicGenetics/Epicosm/blob/master/Twitter_Authorisation.pdf), and there are further details on [Twitter documentation](developer.twitter.com/en/apply-for-access.html) on how to do this.

Please also see these further requirements.

1. Put all repository files and your user list into their own folder, and the script will work out the paths for itself. The python script must be run from the folder it is in.
2. MongoDB version 4 or higher will need to be installed. It does not need to be running, the script will check MongoDB's status, and start it if it is not running. The working database will be stored in the folder where you place your local copy of this repository (not the default location of /data/db). For Linux and MacOS, use your package manager (eg. apt, yum, yast), for example:

`apt install mongodb` (or `yum`, `brew` or other package manager as appropriate)

3. The following Python3 dependencies will need to be installed, and are most easily done with pip:

`apt install python3-pip`

`pip3 install psutil`

`pip3 install tweepy` 

`pip3 install pymongo` 

<p align="center"> ••• </p>

### 2.2 Optional parameters  
The following arguments can be appended:  
`--log`              Create a logfile of all output from the harvest run, in `/epicosm_logs`.

`--refresh`          Refresh the user list (if you want to modify the list of users to harvest from, replace your file `user_list`, and run with `--refresh` so that this is refreshed).

`--get_following`    Gather friend list. This list will go into the MongoDB collection `following`, in the database `twitter_db`. This is normally disabled because API following requests are severely rate-limited.

<p align="center"> ••• </p>

### 3.0 License
DynamicGenetics/Epicosm is licensed under the GNU General Public License v3.0. For full details, please see our [license](https://github.com/DynamicGenetics/Epicosm/blob/master/LICENSE) file. 

Epicosm is written and maintained by [Alastair Tanner](https://github.com/altanner), University of Bristol, Integrative Epidemiology Unit.
