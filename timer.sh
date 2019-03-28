#!/bin/bash

# periodically runs twongo:
# the time duration between runs can be modified by altering
# the sleep time (in seconds), on line 11.

while true;

    do /usr/bin/python3 /twongo/twongo.py --refresh --log;
    
    sleep 3200;
    
    done;
    
