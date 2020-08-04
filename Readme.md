Facebook Group Archiver
=======================

Note: the archiver doesn't work anymore due to Facebook API changes. Currently this tool is only useful for browsing previously archived groups using `viewer.py`.

Dependencies
------------
This archiver needs the `facepy` and `iso8601` packages, while the viewer needs `flask`. To optionally run a production server, we need `apsw`, an interface to `sqlite` that supports read-only access to the database.

```
pip install facepy iso8601 flask
```

[Instructions to install apsw](http://apidoc.apsw.googlecode.com/hg/download.html)

Archiving
----------
Get an access token with `user_groups` permission from [here](https://developers.facebook.com/tools/explorer/). You would need to join facebook developers.


To view groups and their IDs:
```
python archiver.py <access-token>
```

To archive a group, saving into a `sqlite` database:
```
python archiver.py -g <group-id> <access-token>
```

This saves the group into ```<group-id>.db``` in the `databases` directory. If the database already exists, it will attempt to write only new changes to it.

Viewing
-------
To view a group, run:
```
python viewer.py <group-id>
```

This runs a server on `http://localhost:5000` where you can see the stats of the group, do full text searches and provides an interface where you can query the database.

To run a production server:
```
sudo python viewer.py -p <group-id>
```

You will need admin privilages to run the server on port 80, and the `apsw` interface to `sqlite`.

Automating
----------
The script `run.sh` is provided to help automate archiving. For the first time, run:
```
./run.sh
```
This will generate a template configuration file `conf.sh`. Edit the file, following the instructions in it. Every time `run.sh` is ran, it will run the archiver for each group in `FB_GROUPS`, saving it to ```databases/<group-id>.db```, and append the logs to ```logs/<group-id>.log```.

Subsequent runs of `run.sh` will automatically update all the groups in `conf.sh`. One can then use cron to schedule updates. For example to update once per hour (replace `/path/to` with the absolute path of the directory `run.sh` is in ):
```
$ echo "0 * * * * cd /path/to && ./run.sh" | crontab
```


Testing
-------
To run tests:
```
python test.py
```
This will test all the archiving and syncing capabilities of `archiver.py`. These tests do not cover `viewer.py`. These tests are completely independent of Facebook's API, and do not require an internet connection to run.

Updating Schema
---------------
Sometimes the schema of the database in `bootstrap.sql` would update and you would need to apply these updates to existing databases. There will be a branch containing the date of the update with a file `update.sql`. Switch to it and run:
```
./update-db.sh
```
All the databases in `databases/` will be updated, and corresponding logs written to.

Known Problems
--------------
* If during the first archive the archiver is interrupted, it will not archive older posts during subsequent runs.
* Currently a constant number of comments is fetched every time with a hard-coded maximum (currently 1000) without paging. This is because Facebook's comment paging is messed up the last time I tried to use it.
