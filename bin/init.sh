#!/bin/sh

echo "Initializing databases..."
python3 ./bin/init_db.py

echo "Populating Database....."
sqlite3 ./var/primary/mount/games.db < ./share/games.sql
sqlite3 ./database/users.db < ./share/users.sql

echo "Finished Initialization and Population."

exit