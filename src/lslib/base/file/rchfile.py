#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""Resources come in two parts, the standard resource file (*.rc), and the
header file that allows your C/C++ code to reference the elements by ID.

Sometimes your resources for a particular project may get out of sync and
will need to be lined up. ALL element numbers have an ID defined to it. It
just might not be in that one resource. (ie, might not ever be referenced
or have a name assigned to that language, as it may only really be used in
say, the english version)

This is bad form, but it happens. So in these instances, we use the header
file to look up the textual ID for the idnum. (However sometimes you need
to look through a group of header files. In this case check out some of
the global functions provided.) 

WARNING: This is somewhat of a hackish way to provide complete support,
but there realistically is no other way to do this. There are some problems
that may occur when utilizing the header files to match the ids up. For one,
the IDs don't HAVE to match, and also Microsoft uses some weird ID-ing scheme
that reuses ids for different subgroups of ids as well as for different
sections of code. (ie the number 34728 could match up to more than 5 different
IDs.)
"""

import re
import fileinput

###############################################################################
# Our RegEx expressions for matching our fairly easy-to-read header files. The
# expression directly below is really the only one we will ever need. 
###############################################################################
HEADER_LINE_MATCHER = re.compile("^#(define|DEFINE)\s+([A-Z]{2,3}_[0-9a-zA-Z_]+)\s+([0-9]+)$")
IFBLOCK_START = re.compile("^\s*#(ifdef|IFDEF)\s(.+)\s*$")
IFNDEF_LINE   = re.compile("^\s*#(ifndef|IFNDEF)\s(.+)\s*$")
IFBLOCK_END   = re.compile("^\s*#(endif|ENDIF)\s*$")
COMMENT_LINE = re.compile("^//([.\s]+)$")

def findIdInGroup( id, headerLst ):
    """Given a list of header files (complete paths), this function will 
    attempt to find your id and will return a tuple of id->elemnum. 
    """
    lines = _readGroup( headerLst )
    for oid, onum in lines:
        if oid == id: yield oid,onum

def findElemNumInGroup( num, headerLst ):
    """Given a list of header files (complete paths), this function will 
    attempt to find your elemnum and will return a tuple of id->elemnum.
    This is essentially the sister function to findIdInGroup(). 
    """
    lines = _readGroup( headerLst )
    for oid, onum in lines:
        if onum == num: yield oid,onum

def _convertToStrList( headers ):
    """Converts all the headers into strings, in case they were objects."""
    lst = []
    for header in headers:
        if type(header) is not str: 
            lst.append(str(header))
        else: lst.append(header)
    return map(lambda x: x.replace("\\\\","/"), lst) #FIXME: this is a hack!

def _readGroup( headerLst ):
    """Iteratively goes through the list of all headers and tries to find a
    line that matches the HEADER_LINE_MATCHER. 
    """
    lines = fileinput.FileInput(_convertToStrList(headerLst), mode='r')
    for line in lines:
        if HEADER_LINE_MATCHER.search(line) is not None:
            res = HEADER_LINE_MATCHER.search(line).groups()
            if len(res) >= 2: yield tuple(res[-2:])
    

class RCHeaderFile:
    """This object represents a Resource header file on the system. All it
    takes is a path. Notice there are no functions for editing the file. This
    is on purpose as we do not want to wreck the mappings. All we will use this
    class for is searching/parsing.
    """
    def __init__(self, path):
        self._path = path

    def __str__(self): 
        return str(self._path)
        
    def findId(self, id):
        """Returns a tuple of (id,elemnum) when the id given matches a id found
        when reading through the line reader.
        """
        lines = self.__readLines()
        for lid, num in lines:
            if lid == id: return lid, num
        return None, None
        
    def findElemNum(self, num):
        """Returns a tuple of (id,elemnum) when the num given matches an 
        element number found when reading through the line reader.
        """
        lines = self.__readLines()
        for id, elem in lines:
            if elem == num: return id, elem
        return None, None
    
    def __readLines(self):
        global HEADER_LINE_MATCHER
        for line in fileinput.input([self._path], mode='r'):
            if HEADER_LINE_MATCHER.search(line) is not None:
                res = HEADER_LINE_MATCHER.search(line).groups()
                if len(res) >= 2: yield tuple(res[-2:])
    