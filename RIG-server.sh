LOGFILE=RIG-server.log

touch $LOGFILE
sudo python viewer.py -p 251125004903932 >>$LOGFILE 2>&1 &
