#!/bin/bash
#
# THIS FILE WILL LIKELY GO OUT OF DATE QUITE RAPIDLY!!
#
# sets up a fresh container pulled from ubuntu:latest to run twongo.
#
# installing mongodb requires manual interaction sadly....

apt update -y;
apt upgrade -y;
apt install -y zip;
apt install -y jove;
apt install -y git;
# this repository will need to be public, or sign-in required
git clone git://github.com/DynamicGenetics/twongo.git;
apt install -y python3-pip;
pip3 install psutil;
pip3 install tweepy;
pip3 install pymongo;
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4;
echo "deb [ arch=amd64 ] https://repo.mongodb.org/apt/ubuntu bionic/mongodb-org/4.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.0.list;
apt update -y;
# this command wants interaction :(
apt install -y mongodb-org;

