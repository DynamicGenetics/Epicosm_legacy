
<p align="center">
   <a href="https://github.com/DynamicGenetics/Epicosm"><img src="img/epicosmPNGsmall.png" width="300"></a> 
</p>
<p align="center">
   <a href="https://www.python.org/"><img src="img/python_logo.png" width="100" height="80" /></a> 
   <a href="https://www.docker.com/"><img src="img/dynamicgenetics_roundsqua.png" width="80" height="80" /></a> 
   <a href="https://www.mongodb.com/"><img src="img/mongo_logo.png" width="100" height="80" /></a> 
</p>

  ![release](https://img.shields.io/badge/release-1.1-brightgreen)
  [![GPLv3 license](https://img.shields.io/badge/licence-GPL_v3-blue.svg)](http://perso.crans.org/besson/LICENSE.html)
  ![DOI](https://img.shields.io/badge/DOI-TBC-blue.svg)

## Overview
Epicosm: Epidemiology of Cohort Social Media. 
Epicosm is a suite of tools for working with social media data in the context of
epidemiological research. It is aimed for use by epidemiologists who wish to gather, analyse
and integrate social media data with existing longitudinal and cohort-study research.
The tools can:
* Harvest ongoing and retrospective Tweets from a list of users.
* Real-time Twitter stream-listen from geographic locations, and collate into a database.
* Sentiment analysis of Tweets using labMT, Vader and LIWC (dictionary required for LIWC).
* [in development] Validation of sentiment analysis algorithms against groundtruth.

## Instructions in a nutshell
#### 1. [Download the Epicosm repository](https://github.com/DynamicGenetics/Epicosm/archive/master.zip)

#### 2. Install [MongoDB](https://www.mongodb.com/) version 4 or higher:
  * In a Mac terminal `brew install mongodb`
  * In a Linux terminal `apt install mongodb`

#### 3. Put these three files into a folder:
  * `epicosm_mac` OR `epicosm_linux`, as downloaded from the repository in step `1`,
  * `credentials.txt` file (provided here, but complete with [your own Twitter access keys](https://github.com/DynamicGenetics/Epicosm/blob/master/Twitter_Authorisation.pdf)),  
  * and your `user_list` (supplied by you: one screen name per line, plain text file).

#### 4. Run Epicosm from your command line, including your run flags
  * Epicosm will provide some help if it doesn't understand you, just type `./epicosm_linux` or `./epicosm_mac`. See below for more details, but for example a typical harvest can be started with
`./epicosm_linux --user_harvest`

<p align="center"> ••• </p>

## More detail
#### 1 What does it do?  
#### 2 Running Epicosm from compiled python executable
#### 3 Optional parameters
#### 4 Natural Language Processing (Sentiment analysis)
#### 5 Geoharvester
#### 6 Data and other outputs
#### 7 Running the python script manually
#### 8 Licence

<p align="center"> ••• </p>

### 1 What does it do?

Epicosm is a social media harvester, data manager and sentiment analyser. Currently, the platform uses Twitter as the data source and the sentiment analysis methods available are VADER, labMT and LIWC (you will need an LIWC dictionary for this). You provide  a list of users, and it will gather and store all tweets and metadata (going back a maximum of 3240 tweets) for each user. Images, videos and other attachments are stored as URLs. All information is stored by MongoDB. Harvesting can be iterated, for example once a week it can gather new tweets and add them to the database. As well as the full database, output includes a comma-separated-values (.csv) file, with the default fields being the user id number, the tweet id number, time and date, and the tweet content. Epicosm can also harvest the friends of users (ie, *the accounts that the user is following, not the followers of the user*).

Epicosm uses [MongoDB](https://www.mongodb.com/) for data management, and this must be installed before being running Epicosm. This can be done through downloading and installing from the MongoDB website, or it can be done in a Terminal window with the commands
`brew install mongodb` on a Mac
`apt install mongodb` on Linux (Debian-based systems like Ubuntu).

Epicosm can be run in two ways. It can be run using the compiled python executables provided, `epicosm_mac` or `epicosm_linux`. If there are any issues with your input files (your `user_list` and your `credentials.txt`) Epicosm will try to help you. Alternatively, Epicosm can be run by Python version 3+; details are in section 4.

You will need Twitter API credentials by having a developer account authorised by Twitter. Please see our [guide to getting an authorised account](https://github.com/DynamicGenetics/Epicosm/blob/master/Twitter_Authorisation.pdf), and there are further details on [Twitter documentation](developer.twitter.com/en/apply-for-access.html) for how to do this. As of August 2020, Twitter are usually rapid in authorising for academic purposes, although this can of course change. **You will find many guides for getting authorisation which are out of date!**

<p align="center"> ••• </p>

### 2 Running Epicosm from compiled python executable

This is the usual way of running Epicosm (see section 4 for running using Python).

You must provide 2 further files in the folder with the Epicosm executable:
1. a list of user screen names in a file called `user_list`. The user list must be a plain text file, with a single username (twitter screen name) per line.
2. Twitter API credentials. Please see the file in this repository for a template. This file must be called `credentials.txt`.

Then you can run the python executable, for example
`./epicosm_linux [your run flags]` or
`./epicosm_mac [your run flags]`

<p align="center"> ••• </p>

### 3 Optional parameters
When running the harvester, please specify what you want Epicosm to do:

`--user_harvest`        Harvest tweets from all users from a file called user_list
                      (provided by you) with a single user per line. The database will be
                      backed up on every harvest, with a rotating backup of the last three
                      harvests. These can be imported into another instance of MongoDB
                      with `mongoimport`, see MongoDB documentation for details.

`--get_friends`.        Create a database of the users that are
                      being followed by the accounts in your user_list.
                      (This process can be very slow, especially if
                      your users are prolific followers.) You will also get
                      a CSV of users and who they are following, in `/output/csv`
                      If using with --repeat, will only be gathered once.

`--repeat`              Iterate the user harvest every 3 days. This process will need to
                      be put to the background to free your terminal prompt,
                      or to leave running while logged out.

`--refresh`             If you have a new user_list, this will tell Epicosm to
                      take use this file as your updated user list.

`--csv_snapshots`       Make a CSV formatted snapshot of selected fields from every harvest.
                      See documentation for the format and fields of this CSV.
                      Be aware that this may take up disk space - see ./output/csv

Example of single harvest:
`./epicosm --user_harvest`

Example iterated harvest in background, with a renewed user_list and taking CSV snapshots:
`nohup ./epicosm --user_harvest --refresh --csv_snapshots --repeat &`

### 4 Natural Language Processing (Sentiment analysis)

Once you have a database with tweets, you can apply sentiment analysis to each document and insert the result into MongoDB. You will need to run `epicosm_nlp.py` (if you have dependencies errors, please install them with `pip3 install -r requirements.txt`).

To run, specify from the following flags:

`--insert_groundtruth` Provide a file of groundtruth values called 'groundtruth.csv' and insert these into the local database.

`--liwc` Apply LIWC (Pennebaker et al 2015) analysis and append values to the local database. You must have a LIWC dictionary in therun folder, named "LIWC.dic". LIWC has around 70 categories (including posemo and negemo), but many of these will return no value because tweets are too short to provide information. Empty categories are not appended to the database. **Note: the LIWC package is broken and cannot deal with its own dictionary. If it comes across phrasal entries it throws a key error. In LIWC 2015, most of these are variations on the word 'like' ('we like', 'they like', 'not like'), but the words 'like', 'not' 'we' are already in categories, and the phrasal categories have the same metrics anyway! You will need to clean your dictionary with the script in src called `cleanLIWC.sh`. 

`--labmt` Apply labMT (Dodds & Danforth 2011) analysis and append values to the local database. LabMT provides a single positive - negative metric, ranging from -1 to 1 (1 being positive sentiment, 0 being neutral, -1 being negative).

`--vader` Apply VADER (Hutto & Gilbert 2014) analysis and append values to the local database. VADER returns 4 metrics: positive, neutral, negative and compound. See their documentation for details. 

`--textblob` Apply TextBlob (github: @sloria) analysis and append values to the local database. TextBlob provides a single positive - negative metric, ranging from -1 to 1 (1 being positive sentiment, 0 being neutral, -1 being negative).

The results of these analyses will be appended to each tweet's record, under the field "epicosm", and stored in MongoDB.

<p align="center"> ••• </p>

### 5 Geoharvester

The python script `geoharvester.py` can launch a Twitter stream listener by geographic location, as defined by one or more latitude/longitude boxes. Please see the example `geoboxes.py` for the format of this file. As above, you will need to provide your `credentials.txt` to gain access to the Twitter streaming API. All tweets are stored in MongoDB under the database `geotweets` and the collection `geotweets_collection`. To sentiment analyse these, please see the section below on NLP. Few Tweets (historically, less than 2%) have geotags, but Twitter will try to assign a rough location based on city or country. As of 2020, Twitter is reporting they will phase out geotagging, since few people authorise Twitter to geotag their tweets. 

### 6 Data and other outputs
The processed output is a a database of tweets from the users in your `user_list`, and a CSV file, in the folder `./output/csv/`, which by default has the fields: [1] the ID of the tweeter, [2] the id of the tweet, [3] the time and date of the tweet, and [4] the tweet content.

Log files detailing what Epicosm has done is in `/epicosm_logs/`.

Full tweet content and metadata of all tweets is stored in [MongoDB](https://www.mongodb.com/) in a format which is closely aligned with JSON. To work with full raw data, you will need MongoDB installed. The tweet database is named `twitter_db`, with two collections `tweets`, and `friends` which contains a list of all users that each user in your list are following. The `friends` collection will only be made if you ask for friends lists to be gathered. *Currently, gathering friends list causes the process to be heavily rate limited by Twitter! [solution in progress]*

A backup of the entire database is stored in `/output/twitter_db/`. If you have MongoDB installed, this can be restored with the command

`mongorestore [your name given to the database] [the path to the mongodump bson file]`

for example:

`mongoresotore -d twitter_db ./output/twitter_db/tweets.bson`

(However, please check [MongoDB documentation](https://docs.mongodb.com/manual/) as commands can change)

To view and interact with the database using a GUI, you will need MongoDB installed, and a database viewer. Of open source options, we find that [Robo 3T](https://robomongo.org/) works very well.

<p align="center"> ••• </p>

### 7 Running the python script manually

See the source file in `/src` and run it with

`python3 epicosm.py [your run flag]`

You must provide 2 files:
1. a list of user screen names in a file called `user_list`. The user list must be a plain text file, with a single username (twitter screen name) per line.  
2. Twitter API credentials will need to be supplied, by editing the file `credentials.py` (further instructions inside file). You will need your own Twitter API credentials by having a developer account authorised by Twitter, and generating the required codes. Please see [our guide](https://github.com/DynamicGenetics/Epicosm/blob/master/Twitter_Authorisation.pdf), and there are further details on [Twitter documentation](developer.twitter.com/en/apply-for-access.html) on how to do this.

Please also see these further requirements.

1. Put all repository files and your user list into their own folder. The python script must be run from the folder it is in.
2. MongoDB version 4 or higher will need to be installed. It does not need to be running, the script will check MongoDB's status, and start it if it is not running. The working database will be stored in the folder where you place your local copy of this repository (not the default location of /data/db). For Linux and MacOS, use your package manager (eg. apt, yum, yast), for example:

`apt install mongodb` (or `yum`, `brew` or other package manager as appropriate)

3. The following Python3 dependencies will need to be installed from the `src/requirements.txt` file if you run 

`pip3 install -r requirements.txt`

<p align="center"> ••• </p>

### 8 Licence
DynamicGenetics/Epicosm is licensed under the GNU General Public License v3.0. For full details, please see our [license](https://github.com/DynamicGenetics/Epicosm/blob/master/LICENSE) file. 

Epicosm is written and maintained by [Alastair Tanner](https://github.com/altanner), University of Bristol, Integrative Epidemiology Unit.
