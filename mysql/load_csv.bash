#!/bin/bash

tables="
auth
user
session

org
address
note
orgtag
org_address
org_orgtag
org_note
address_note
orgtag_note

note_fts

address_note_v
address_v
note_v
org_address_v
org_note_v
org_orgtag_v
org_v
orgtag_note_v
orgtag_v
"

echo "SET foreign_key_checks = 0;"

for table in $tables
do
    fields=$(cat "/tmp/mango-sql/$table.row")
echo "LOAD DATA LOCAL INFILE '/tmp/mango-sql/$table.csv' 
REPLACE
INTO TABLE $table
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '\"'
LINES TERMINATED BY '\n'
($fields);
"
done



echo "SET foreign_key_checks = 1;"

# mysql  --local-infile < blah.sql

