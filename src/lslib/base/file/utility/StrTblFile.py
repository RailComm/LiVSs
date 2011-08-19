#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""A StrTblFile (*.strtbl) is a file that contains one or more string table 
that are used within a given project. What is good about a string table file is 
that a single string table can contain all of its language/resource data so 
that it can be exported to multiple (or preferably ALL) of your resource files.

The Format of a dialog file is as follows:
                            [HEADER]
                            [ENTRY]
                            [ENTRY]
                            ...
                            
Each of these [*] represents a line in the file. The description of each line 
is next:

Header - This is the line that defines what each column represents. See below.
        
Entry - A String value that was present in the string table. However its a
        double mapping ID->Value, and LangCode->Value.
        
The following is the definition of the header's columns and their position
    
                        id,langcode1,langcode2,...
id - the id of the Entry (the string value ie IDC_BYLOCATIONCHECK, etc).

langcode# - this is substituted with the actual language code. To make the 
        columns look similar to: 'id,1033,2058'. This may be changed later
        to make it more readable (ie '1033-en-US', but what these columns 
        represent will never change.)
"""

from lslib.base.file.lscsv import LSCSV
from lslib.base.file.msrcobj.stringtable import RCStrTbl
from lslib.base.file.msrcobj.msobjbase   import RCStringValue


def ScanStringTableFile( stringTableFile, headerLst ):
    """Scan through the headers and make sure the file is correct."""
    from lslib.base.file.rchfile import findElemNumInGroup
    def _scanNodeList( values ):
        for val in values:
            if val.reqIDScan():
                searcher = findElemNumInGroup( val.getID().num , headerLst )
                for lid,_ in searcher: val.addPossibleID( lid )
    if stringTableFile._table is not None:      
        _scanNodeList( stringTableFile._table._values )

def InMemTable( path, table ):
    """An easy way to get a new file in one line. If you want to just save
    a group of menus."""
    import copy
    f = RCStrTblFile( path )
    f._table = copy.deepcopy(table)
    return f


class RCStrTblFile(LSCSV):
    """ A String table File is essentially an CSV file that is used to house
    all of the string table information for any MSVS project in such a way as 
    to be able to quickly pull out or push back language information. 
    """ 
    HEADER_ROW  = 0
    HEADER_COLS = ['id']
    CONTROL_COLS = 1
    
    def __init__(self, path):
        ## We are a CSV file but without sections enabled.
        super().__init__( path )
        self._table = None
        
    def getValue(self, id, langcode='1033', default=None):
        """Utility function for getting the value from the string table files'
        table.
        """
        return self._table.getValue(id, langcode, default)
        
    def addStrTable(self, other):
        """Adds another string table to the current file. This will merge the
        two string tables into one so it can be loaded and saved.
        """
        if self._table is None:
            self._table = other
        else:
            self._table.addStringTable(other)
        
    @staticmethod        
    def merge( newpath, firstStrTblFile, secondStrTblFile, preloaded=True, bypassScan=False ):
        """Merges two dialog files, this may be important during the step to get ALL 
        RCDialogFiles into the translation files.
        """
        import copy 
        totalTables = RCStrTblFile( newpath )
        
        first  = copy.deepcopy( firstStrTblFile._table )
        second = copy.deepcopy( secondStrTblFile._table )
        
        totalTables._table = RCStrTbl.mergeTables(first, second)
                
        #return our newly made String Table
        return totalTables
    
    def update(self, otherStrTblFile ):
        """Updates this file with the values present in the other, it will NOT 
        add new values, and will NOT change the order. It will only add new 
        langcodes and adjust already present ones.
        """
        self._table.updateValues( otherStrTblFile._table )
    
    def save(self, newpath=None):
        """Save the current RCStrTblFile to its path."""
        if self._table is None: return
        if newpath is not None: self._path = newpath
        # create header
        lst = {}
        for l in self._table.getPossibleLangs(): lst[l]=1
        langorder = list(lst.keys())
        header = RCStrTblFile.HEADER_COLS+langorder
        
        # build lines
        lines = self.__buildLines( self._table, langorder )
             
        # write lines
        writer = self.writeLine(header)
        self.writeLines(lines, writer)
    
    def load(self):
        """Load the string tables into memory."""
        offset = RCStrTblFile.CONTROL_COLS
        header = self.getHeader( RCStrTblFile.HEADER_ROW )
        if len(header) < offset: 
            raise Exception("File does not have enough control columns.")
        
        langcodes = len(header)-offset;
        lines = self.readLine(RCStrTblFile.HEADER_ROW+1)
        self._table = RCStrTbl()
        for line in lines: #For each line add it to the string table
            value = RCStringValue(line[0]) #id
            ####################################
            # For each langcode column add it to the string value.
            for c in range(langcodes):
                value.addValuePair(header[offset+c], line[offset+c])
            self._table._values.append(value)
        return True

    def __buildLines(self, table, langorder):
        ### Builds a 2D list of lists that are the entries for saving the 
        ### given table.
        if len(langorder) == 0: return []
        lines = []
        for entry in table._values:
            line = [entry.getID()]
            for lang in langorder:
                line.append(entry.getValue(lang,''))
            lines.append(line)        
        return lines
        