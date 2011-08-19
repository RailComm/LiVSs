#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
""" A string table is a mapping from a string constant to an ID. This ID
can be referenced in code in order to utilize the constant. Here is an
example of a string table:

STRINGTABLE
BEGIN
    AFX_IDS_SCRESTORE       "Restore the window to normal size"
    AFX_IDS_SCTASKLIST      "Activate Task List"
    AFX_IDS_MDICHILD        "Activate this window"
END

To see how this object is parsed out of the resource file. Take a look
at the StrTbleFile.py object in lslib.base.file.utility.
"""

class RCStrTbl: 
    """The RCStrTbl is the object stored in memory that represents a single
    String table within one or more resource files (eg, one or more languages).
    """
    def __init__(self):
        self._values = []
        
    def addStringTable(self, other, merge=True, overwriteLangCode=False):
        """Similar to merge, but its in place and adds all the other values 
        to this current one.
        """
        if other._values is None or len(other._values)==0: return
        for val in other._values: 
            self.addStringValue( val, merge, overwriteLangCode )
        
    def addStringValue(self, other, merge=True, overwriteLangCode=False):
        """Adds a string value to the table. If the ID already exists the two
        Values are combined.
        """
        if not self.hasValue(other.getID()):
            self._values.append( other )
        elif merge:
            for val in self._values:
                if val.getID() == other.getID(): 
                    val.combine( other )
                    break
                
    def updateValues(self, otherTable):
        """Update all values with the values in the other table. This means 
        that NO NEW VALUES ARE ADDED, it just overwrites the values in the
        current table with the values in the other. It also allows for adding 
        new language codes for each particular value.
        """
        for index in range(len(self._values)):
            for oval in otherTable._values:
                if self._values[index].getID() == oval.getID():
                    self._values[index].combine( oval, intelligent=False )
                    break
                
    @staticmethod
    def mergeTables(first, second):
        """Merge two string tables. It checks all of the IDs and makes sure
        it merges the string values correctly. This function returns a new
        string table and doesn't affect the other two.
        """
        newTable = RCStrTbl()
        if first is not None: newTable.addStringTable( first )
        if second is not None: newTable.addStringTable( second )
        return newTable
    
    def getValue(self, id, langcode='1033', default=None):
        """Gets the value of a given ID found in the string table."""
        for val in self._values:
            if val.getID() == id:
                return val.getValue(langcode, default)
        return default
    
    def hasValue(self, id):
        """Checks if the id is present in the string table."""
        for val in self._values: 
            if val.getID() == id: return True
        return False
    
    def getPossibleLangs(self):
        """Used when deriving the headers for a RCStrTblFile."""
        lst = {}
        for e in self._values:
            for lang in e.getLangCodes():
                lst[ lang ] = 1
        return lst.keys()