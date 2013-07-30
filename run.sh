#!/bin/bash

if [ -f conf.sh ]
then
    source conf.sh
else
    echo "# This file contains the settings needed to run the archiver:" > conf.sh
    echo "#" >> conf.sh
    echo "# TOKEN:      Facebook access token needed to download a group" >> conf.sh
    echo "# PATH_TO:    Directory containing archiver.py" >> conf.sh
    echo "# FB_GROUPS:  Array of facebook group IDs to archive" >> conf.sh
    echo "# GROUPNAMES: Array of human-readable names corresponding to FB_GROUPS" >> conf.sh
    echo -e '\nTOKEN=""\nPATH_TO=' `pwd` '\nFB_GROUPS=("")\nGROUPNAMES=("")' >> conf.sh

    echo "Please edit conf.sh and run again"
    exit 0
fi

gLen=${#FB_GROUPS[@]}
LOGPATH=$PATH_TO/logs
DBPATH=$PATH_TO/databases

mkdir -p $LOGPATH

for (( i=0; i< ${gLen}; i++ ));
do
    ID=${FB_GROUPS[$i]}
    NAME=${GROUPNAMES[$i]}

    LOGFILE=$LOGPATH/$ID.log
    touch $LOGFILE
    echo "" >> $LOGFILE
    date >> $LOGFILE
    python $PATH_TO/archiver.py $@ -g $ID $TOKEN >>$LOGFILE 2>&1

    # Make symlinks
    if [ ! -f $DBPATH/$NAME.db ]
    then
        ln -s $DBPATH/$ID.db $DBPATH/$NAME.db
    fi

    if [ ! -f $LOGPATH/$NAME.log ]
    then
        ln -s $LOGPATH/$ID.log $LOGPATH/$NAME.log
    fi
done
