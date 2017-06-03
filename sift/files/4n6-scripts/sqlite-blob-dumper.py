# sqlite-blob-dumper.py = Python script to dump BLOB fields from SQLite DBs
#
# Copyright (C) 2015 Adrian Leong (cheeky4n6monkey@gmail.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You can view the GNU General Public License at <http://www.gnu.org/licenses/>
#
# Version History:
# v2015-07-03 Initial Version
#
# It was developed/tested on Ubuntu 14.04 LTS running Python v2.7.6.
# Also tested on Win7x64 running Python 2.7.6
#
# Usage Example:
# python sqlite-blob-dumper.py targetdb.sqlite tablename outputdir
#

import sys
import argparse
import sqlite3
import os
from os import path

# Function to compose a filename string based on table name, column name, rowid and
# on first several bytes of BLOB
# File signatures sourced from http://www.garykessler.net/library/file_sigs.html
def calculate_filename(table, colname, rowid, blob):
    ext = ".blob"
    if (blob[0:2] == "\xFF\xD8") :
        ext = ".jpg"
    elif (blob[0:8] == "\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"):
        ext = ".png"
    elif (blob[0:4] == "\x50\x4B\x03\x04"):
        ext = ".zip"
    elif (blob[0:6] == "\x62\x70\x6C\x69\x73\x74"):
        ext = ".bplist"
    elif (blob[0:11] == "\x00\x00\x00\x14\x66\x74\x79\x70\x33\x67\x70"):
        ext = ".3gp" # as per https://en.wikipedia.org/wiki/3GP_and_3G2
    elif (blob[0:11] == "\x00\x00\x00\x20\x66\x74\x79\x70\x33\x67\x70"):
        ext = ".3g2" # as per https://en.wikipedia.org/wiki/3GP_and_3G2       
    elif (blob[0:5] == "\x23\x21\x41\x4D\x52"):
        ext = ".amr" # for iOS voicemail

    name = table + "_row_" + rowid + "_" + colname + ext
    return(name)
# Ends function


version_string = "sqlite-blob-dumper.py v2015-07-03"
print "Running " + version_string + "\n"

parser = argparse.ArgumentParser(description='Extracts BLOB fields from a given SQLite Database')
parser.add_argument("db", help='SQLite DB filename')
parser.add_argument("table", help='SQLite DB table name containing BLOB(s)')
parser.add_argument("outputdir", help='Output directory for storing extracted BLOBs')

args = parser.parse_args()

# Check DB file exists before trying to connect
if path.isfile(args.db):
    dbcon = sqlite3.connect(args.db)
else:
    print(args.db + " file does not exist!")
    exit(-1)

if not os.path.isdir(args.outputdir):
    print("Creating outputdir directory ...")
    os.mkdir(args.outputdir)

# Determine Primary Key (for ordering query by) and column names (for labelling)
query = "pragma table_info("+ args.table +")"
cursor = dbcon.cursor()
cursor.execute(query)
tableinforow = cursor.fetchone()

pkname = "" # Stores primary key name
columnnames = [] # Stores list of column names (for use later in query)

while (tableinforow):
    #print(tableinforow)
    cols = len(tableinforow)
    # Ass-umes "table_info" query returns row cols in the following order:
    # ColumnID (0), Name(1), Type(2), NotNull(3), DefaultValue(4), PrimaryKey(5)
    # Each row returned represents a table column
    if (tableinforow[cols-1]): # Last col (PrimaryKey) should be 1 if col is PrimaryKey
        pkname = tableinforow[1] # Set pkname if Primary key
    if (tableinforow[2] == "BLOB"): # Check if Type is BLOB
        columnnames.append(tableinforow[1]) # Store list of BLOB column names
    tableinforow = cursor.fetchone()
# Ends while row

if (pkname is ""):
    print("Unable to find Primary Key in DB ... Exiting")
    exit(-1)
else:   
    print("Primary Key name is: " + pkname)

if (len(columnnames) == 0):
    print("No BLOB columns detected ... Exiting")
    exit(-1)

# Construct column names string for use in query
# eg "blob1, blob2, blob3"
# Also keep track of order in which they'll be queried/returned
qcolnames = ""
numblobcols = len(columnnames)
for colidx in range(numblobcols):
    if (colidx == (numblobcols - 1)):
        qcolnames += columnnames[colidx] # Last colname doesn't need a comma
    else:
        qcolnames += columnnames[colidx] + ", "
        
print("Detecting BLOB columns = " + qcolnames)

# Query grabs the primary key field and each BLOB column. 
# It orders by primary key (ass-umes there's only 1 PK)
query = "SELECT " + pkname + ", " + qcolnames + " FROM " + args.table + " ORDER BY " + pkname + ";"
cursor = dbcon.cursor()
cursor.execute(query)

# Row order will be pk value then BLOB column(s) 
row = cursor.fetchone()
while row:
    try:
        # blobcolidx = Query row index for a BLOB col (there can be more than 1 BLOB in a row)
        # Ass-umes PK is NOT a BLOB
        for col in columnnames:
            blobcolidx = columnnames.index(col) + 1 # Get query row index for this blob col
            # Need to add 1 to account for PK field (at row[0])
            # Arg order is tablename, colname, PK rowid, blob
            name = calculate_filename(args.table, col, str(row[0]), bytes(row[blobcolidx])) 
            fullname = os.path.join(args.outputdir, name)
            print("Extracting ... " + fullname)
            outputfile = open(fullname, "wb")
            outputfile.write(bytes(row[blobcolidx])) # Write blob
            outputfile.close()
    except :
        print("Bad BLOB extract for row " + str(row[0]) + " ... Skipping the row & continuing on")
        exctype, value = sys.exc_info()[:2]
        print ("Exception type = ",exctype,", value = ",value)
        row = cursor.fetchone()
        continue # Skip to next loop if error here

    row = cursor.fetchone() # Normal end of loop

cursor.close()
dbcon.close()

print "\nExiting ..."
exit(0)


