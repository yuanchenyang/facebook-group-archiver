#!/bin/bash

if [ -f conf.sh ]
then 
    source conf.sh
else
    echo "Nothing to update!"
fi

LOGPATH=$PATH_TO/logs
DBPATH=$PATH_TO/databases

for ID in ${FB_GROUPS[@]}
do
    LOGFILE=$LOGPATH/$ID.log
    touch $LOGFILE
    echo -e "\nUpdating Database" >> $LOGFILE
    date >> $LOGFILE
    
    cat $PATH_TO/update.sql | sqlite3 $DBPATH/$ID.db >> $LOGFILE 2>&1
    python $PATH_TO/archiver.py -u -g $ID $TOKEN >> $LOGFILE 2>&1
done
