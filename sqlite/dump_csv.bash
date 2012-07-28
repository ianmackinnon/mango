#!/bin/bash

mkdir -p /tmp/mango-sql

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

for table in $tables
do
    echo $table;
    echo -en ".mode csv
.header on
.out /tmp/mango-sql/$table.csv
select * from $table;
" | sqlite3 mango.db
    head -n 1 /tmp/mango-sql/$table.csv > /tmp/mango-sql/$table.row
    sed -i '1d' /tmp/mango-sql/$table.csv
done

table="note_fts"
echo $table;
echo -en ".mode csv
.header on
.out /tmp/mango-sql/$table.csv
select docid, content from $table;
" | sqlite3 mango.db
head -n 1 /tmp/mango-sql/$table.csv > /tmp/mango-sql/$table.row
sed -i '1d' /tmp/mango-sql/$table.csv
