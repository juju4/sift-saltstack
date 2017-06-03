#! /usr/bin/env python

# Python script to parse Contacts from a Windows 8.0 phone's store.vol file
# Author: cheeky4n6monkey@gmail.com (Adrian Leong)
# 
# Special Thanks to Detective Cindy Murphy (@cindymurph) and the Madison, WI Police Department 
# for the initial test data and encouragement.
# Thanks also to Brian McGarry (Garda) and JoAnn Gibb (Ohio Attorney Generals Office) for providing test data/feedback.
#
# WARNING: This program is provided "as-is" and has been tested on a limited set of data from a Nokia Lumia 520 Windows Phone 8
# See http://cheeky4n6monkey.blogspot.com/ for further details.

# Copyright (C) 2014, 2015 Adrian Leong (cheeky4n6monkey@gmail.com)
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

# The MPD store.vol Contact record structures for a Phonebook type entry look like one of the following:
# MPD format 1:
# [?][0x1][19 Digits][0x1][Name1][0x1][Name2][0x1][Name3][0x1][Name4][0x1][Name5][0x1][Phone1][0x1][Codestring][0x1][Phone2][0x1][Name6][0x1][Name7][01 04 00 00 00 82 00 E0 00 74 C5 B7 10 1A 82 E0 08]
#
# Note: Above fields contain null-terminated Unicode strings and Codestring is something like "ABCH".
#
# MPD format 2:
# [?][0x1][Name1][0x1][Name2][0x1][Name3][0x1][Name4][0x1][Name5][0x1][Phone1][0x1][Phone2][0x1][Name6][0x1][Name7][01 04 00 00 00 82 00 E0 00 74 C5 B7 10 1A 82 E0 08]
#
# Note: Above fields contain null-terminated Unicode strings.
#
# The MPD Hotmail type entry (only one was found) is:  
# [?][0x1][19 Digits][0x1][Name1][0x1][Name2][0x1][Name3][0x1][Name4][0x1][Codestring][0x1][0x8 bytes][0x1][Name5][0x1][Name6][0x1][Email][01 04 00 00 00 82 00 E0 00 74 C5 B7 10 1A 82 E0 08]
#
# Note: All fields except for the (binary) 0x8 bytes in the middle contain null-terminated Unicode strings
#
# The Garda Contact records appear to follow these 3 patterns:
# Garda format 1:
# [?][0x1][19 Digits][0x1][Name1][0x1][Name2][0x1][Name3][0x1][Name4][0x1][Name5][0x1][Phone1][0x1][Codestring][0x1][GUID][0x1][Phone2][0x1][Name6][0x1][Name7][01 04 00 00 00 82 00 E0 00 74 C5 B7 10 1A 82 E0 08]
#
# Note: All fields above contain null-terminated Unicode strings. This is the same as MPD format 1 but with an additional GUID string.
#
# Garda format 2:
# [?][0x1][Name1][0x1][Name2][0x1][Name3][0x1][Name4][0x1][Name5][0x1][Country][0x1][City][0x1][Phone1][0x1][handle][0x1][Phone2][0x1][Name6][0x1][Name7][01 04 00 00 00 82 00 E0 00 74 C5 B7 10 1A 82 E0 08]
# Note: Above Name strings contained non-Unicode characters in some instances. There was also a potential email handle field (eg "firstname.lastname").
#
# Garda format 3:
# [?][0x1][Name1][0x1][Name2][0x1][Name3][0x1][Name4][0x1][Name5][0x1][Name6][0x1][Name7][0x1][Name8][01 04 00 00 00 82 00 E0 00 74 C5 B7 10 1A 82 E0 08]
#
# Note: All fields above contain repeated null-terminated Unicode strings and appear to be a login id. Name7 contained non-Unicode characters.
#
# The script will search for instances of [01 04 00 00 00 82 00 E0 00 74 C5 B7 10 1A 82 E0 08]
# and then try reading the previous Unicode string fields in reverse order. 
# The last field should contain the Name but can also hold Email for an MPD Hotmail entry.
# The 3rd last field should contain the Phone number but can also hold Name for MPD Hotmail/Garda3 type entries. 
#
# History
# v2014-08-17 Initial version
# v2014-08-21 Adjusted to extract last three Unicode fields only
# v2014-10-05 Renamed script from "win8contacts.py" to "wp8-contacts.py"
# v2015-07-12 Changed script to search for hex strings in chunks of CHUNK_SIZE rather than in one big read 
#            (makes it quicker when running against whole .bin files). Thanks to Boss Rob :)
# v2015-08-19 Fixed bug in chunking code where it was not processing the last chunk properly
#

import codecs
import os
import sys
import string
from optparse import OptionParser
import re
import os
import math

version_string = "wp8-contacts.py v2015-08-19"
CHUNK_SIZE = 2000000000 # max value of CHUNK_SIZE + DELTA is 2147483647 (C long limit with Python 2)
DELTA = 1000 # read this extra bit to catch any hits crossing chunk boundaries. Should be AT LEAST max size of record being searched for.

# Find all indices of the "pattern" regular expression in a given string (using regex)
# Where pattern is a compiled Python re pattern object (ie the output of "re.compile")
def regsearch(bigstring, pattern, listindex=[]):
    hitsit = pattern.finditer(bigstring)
    for it in hitsit:
        # iterators only last for one shot so we capture the offsets to a list
        listindex.append(it.start())
    return listindex

# Extract a Unicode null terminated string given file pointer to terminating null character. 
# Starts at the beginning of last (null) Unicode char and 
# reads Unicode string in reverse. Returns read string or "Error!"
def rev_extract_unistring(f):
    readchar = 0xABCD
    readcharlist = []
    flag = True
    charcount = 0
    begin = f.tell()
    while (flag):
        try:
            readchar = f.read(1)
            charcount += 1
            if ( (readchar == unichr(0)) and (charcount > 1) ): # bailout if null char and not null at end of string
                flag = False
            else:
                if ( (readchar == unichr(0)) and (charcount == 1) ): # skip null at end of string
                    f.seek(f.tell() - 4) # jump back to the previous Unicode char
                    continue
                if (readchar in string.printable): # record each printable char in list
                    #print "readchar = " + readchar
                    readcharlist.insert(0, readchar)
                    f.seek(f.tell() - 4)
                else:
                    #print "Unprintable Unicode char at " + hex(f.tell() - 2).rstrip("L")
                    flag = False # unprintable means we've gone past first char of string / invalid string
        except:
            print "Unicode read error at offset " + hex(begin).rstrip("L")
            exctype, value = sys.exc_info()[:2]
            print ("Exception type = ",exctype,", value = ",value) 
            return "Error!"
    
    readstring = ''.join(readcharlist) # convert the list into a string
    return readstring

# Searches chunks of a file (using RE) and returns file offsets of any hits.
# Intended for searching of large files where we cant read the whole thing into memory
# This function calls the "regsearch" search method
def sliceNsearchRE(fd, chunksize, delta, term):
    final_hitlist = [] # list of file offsets which contain the search term
    pattern = re.compile(term, re.DOTALL) # should only really call this once at start, if same substring.
    stats = os.fstat(fd.fileno())
    #print("sliceNsearchRE Input file " + filename + " is " + str(stats.st_size) + " bytes\n")
    begin_chunk = 0

    # Handle if filesize is less than CHUNK_SIZE (eg store.vol instead of image.bin)
    # Should be able to read whole file in 1 chunk 
    if (chunksize >= stats.st_size):
        fd.seek(begin_chunk)
        raw = fd.read()
        final_hitlist = regsearch(raw, pattern, [])
        #print(str(len(final_hitlist)) + " hits found in 1 chunk for " + str(term))
    else:
        # Filesize is greater than 1 chunk, need to loop thru
        numchunks = int(math.ceil(float(stats.st_size) / chunksize))
        #print("numchunks required = " + str(numchunks))
        chunk_size_to_read = chunksize + delta
        for chunknum in range(numchunks):
            if ((chunk_size_to_read + begin_chunk) > stats.st_size):
                chunk_size_to_read = stats.st_size - begin_chunk
            #print("seeking " + str(begin_chunk) + " with size = " + str(chunk_size_to_read))
            fd.seek(begin_chunk)
            rawchunk = fd.read(chunk_size_to_read)
            subhits = regsearch(rawchunk, pattern, [])
            #print(str(len(subhits)) + " hits found at " + str(subhits))
            # Items in subhits will be offsets relative to the start of the rawchunk (not relative to the file)
            # Need to adjust offsets ...
            for hit in subhits :
                if (hit < chunksize) :
                    final_hitlist.append(begin_chunk + hit)
                    #print("adding " + str(begin_chunk + hit) + " to list")
                elif (hit >= chunksize) :
                    #print("ignoring " + str(begin_chunk + hit) + " to list")
                    break # don't care if we get here because hit should be processed in next chunk
                    # subhits can start at index 0 so possible hit offsets are 0 to chunksize-1 inclusive
            begin_chunk += chunksize
    #print("final_hitlist = " + str(final_hitlist))
    return(final_hitlist)

# Main
print "Running " + version_string + "\n"
usage = " %prog -f inputfile -o outputfile"

# Handle command line args
parser = OptionParser(usage=usage)
parser.add_option("-f", dest="filename", 
                  action="store", type="string",
                  help="Input File To Be Searched")
parser.add_option("-o", dest="tsvfile",
                  action="store", type="string",
                  help="Tab Separated Output Filename")
(options, args) = parser.parse_args()

# Check if no arguments given by user, exit
if len(sys.argv) == 1:
    parser.print_help()
    exit(-1)
if (options.filename == None) :
    parser.print_help()
    print "\nInput filename incorrectly specified!"
    exit(-1)
if (options.tsvfile == None) :
    parser.print_help()
    print "\nOutput filename incorrectly specified!"
    exit(-1)

# Open store.vol for unicode encoded text reads
try:
	funi = codecs.open(options.filename, encoding="utf-16-le", mode="r")
except:
    print ("Input File Not Found (unicode attempt)")
    exit(-1)

# Open store.vol for binary byte ops (eg timestamps)
try:
	fb = open(options.filename, "rb")
except:
    print ("Input File Not Found (binary attempt)")
    exit(-1)

# search the file chunk strings for the
# [01 04 00 00 00 82 00 E0 00 74 C5 B7 10 1A 82 E0 08] value which appears at end of Contact records
contact_sig = "\x01\x04\x00\x00\x00\x82\x00\xE0\x00\x74\xC5\xB7\x10\x1A\x82\xE0\x08"
contact_hits = sliceNsearchRE(fb, CHUNK_SIZE, DELTA, contact_sig)
print "Found " + str(len(contact_hits)) + " potential contacts" 

# Dict for storing results (keyed by offset)
contact_entries = {}

for hit in contact_hits:
    #print "Contact Hit at " + hex(hit).rstrip("L")
    next_offset = hit-0x2
    #print "1st offset = " + hex(next_offset).rstrip("L")
    funi.seek(next_offset)
    # Usually the name field / can also be email
    last_field_str = rev_extract_unistring(funi)
    #print "last_field_str = " + last_field_str
    # If good read on last field, continue reading next field
    if (last_field_str != "Error!"):
        next_offset = funi.tell()-0x3
        #print "2nd offset = " + hex(next_offset).rstrip("L")
        funi.seek(next_offset)
        second_last_field_str = rev_extract_unistring(funi)
        #print "second_last_field_str = " + second_last_field_str
    else:
        second_last_field_str = "Error!"
    if (second_last_field_str != "Error!"):
        next_offset = funi.tell()-0x3
        #print "3rd offset = " + hex(next_offset).rstrip("L")
        funi.seek(next_offset)
        # Usually the phone field / can also be name
        third_last_field_str = rev_extract_unistring(funi)
        #print "third_last_field_str = " + third_last_field_str
    else:
        third_last_field_str = "Error!"

    contact_entries[hit] = (last_field_str, third_last_field_str)

fb.close()
funi.close()

print "\nRetrieved " + str(len(contact_entries)) + " contacts" 

# sort by name field
sorted_contact_keys = sorted(contact_entries, key = lambda x : (contact_entries[x][0], contact_entries[x][0])) 

# print to TSV
# open contacts output file if reqd
if (options.tsvfile != None):
    try:
        tsvof = open(options.tsvfile, "w")
    except:
        print ("Trouble Opening TSV Output File")
        exit(-1)
    tsvof.write("Offset\tLast_Field(Name)\tThird_Last_Field(Phone)\n")

    for key in sorted_contact_keys:
        tsvof.write(hex(key).rstrip("L") + "\t" + contact_entries[key][0] + "\t" + contact_entries[key][1] + "\n")

    print "Finished writing out TSV"
    tsvof.close()


