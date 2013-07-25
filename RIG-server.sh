LOGFILE=RIG-server.log

touch $LOGFILE
sudo python viewer.py 251125004903932 >> $LOGFILE &
