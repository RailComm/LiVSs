#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""String Table files on a project level are standard CSV files and have no 
distinguishing marks (which makes it easy to differentiate from a dialog file).
However on the System level each string table group gets a section header like 
so:   
                            [[ project name ]]
Notice the double brackets. This makes it easy to differentiate between 
standard string table files but also any of the dialog files.
All parsing of this file type happens in the SysStrTblFile object, and 
shouldn't be moved as there is no need to delve much deeper than what 
functions are provided via the BaseUtilityFileWrapper object. Any 
accessors can be pushed to a per-project level.   
"""
import re
import copy
import logging

from lslib.base.file.lscsv               import LSCSV
from lslib.base.file.msrcobj.stringtable import RCStrTbl
from lslib.base.file.utility.StrTblFile  import RCStrTblFile, InMemTable
from lslib.base.file.msrcobj.msobjbase   import RCStringValue
from lslib.base.file.syslvl.sysbase      import BaseUtilityFileWrapper, \
                                                isSystemLevelStringTable

SEC_NAME = re.compile("^\[(.*?)\]")

class SysStrTblFile( BaseUtilityFileWrapper, LSCSV ):
    """This is the object that allows you to pull individual projects' string
    table files in and out of the master System String Table Files. To 
    utilize it, just give it a path name of the system file and call load.
    """
    def __init__(self, path): 
        if not isSystemLevelStringTable( path ):
            raise TypeError("Path given is not a system level string table file.")
        super().__init__( path )
        self.setHasSections( True )
        self._projs = {} #map: "projName" -> RCStrTbl
        
    def load(self, newpath=None):
        offset = RCStrTblFile.CONTROL_COLS
        header = self.getHeader( RCStrTblFile.HEADER_ROW )
        if len(header) < offset: 
            raise Exception("File does not have enough control columns.")
        
        langcodes = len(header)-offset;
        sections = self.readSection(RCStrTblFile.HEADER_ROW+1)
        for secname, entries in sections:
            name = self.__cleanName( secname )
            self._projs[name] = RCStrTbl()
            for entry in entries:
                value = RCStringValue(entry[0])
                for c in range(langcodes):
                    value.addValuePair(header[offset+c], entry[offset+c])
                self._projs[name].addStringValue( value )
        self.__loaded = True
        
    def save(self, newpath=None):
        # we don't care about checking if its syslvl, we are overwriting.
        if newpath is not None: self._path = newpath
        #create header:
        lst = {}
        for table in self._projs.values():
            if table is None: continue
            for l in table.getPossibleLangs(): lst[l]=1
        langorder = list(lst.keys())
        header = RCStrTblFile.HEADER_COLS+langorder
        sections = {}
        #generate sections
        for name, table in self._projs.items():
            if table is None: table=RCStrTbl()
            section = "[%s]"%name
            sections[section] = self.__buildLines(table, langorder)
        #write sections
        try:
            writer = self.writeLine( header )
            self.writeSections(sections, writer)
        except: 
            raise
    
    
    def getProjectList(self):
        return list(self._projs.keys())
    
    def removeProjLevelFile(self, projName): 
        return self._projs.pop(projName, None) is not None
    
    def addProjLevelFile(self, projName, path, obj=None, overwrite=True): 
        if not overwrite and projName in self._projs:
            raise KeyError("Project already exists!")
        if obj is not None:
            file = obj
        else:
            file = RCStrTblFile( path )
            if not file.load():
                raise Exception("Could not load String Table File: %s"%path)
        self._projs[projName] = copy.deepcopy( file._table )
        return True
    
    def genProjLevelFile(self, projName, newPath, autosave=False): 
        if projName not in self._projs:
            raise KeyError("Project wasn't found in the system file.")
        file = InMemTable( newPath, self._projs[projName] )
        if autosave: file.save()
        return file
    
    def updateFromTranslation(self, otherSysFile, autosave=False):
        for proj in self._projs.keys():
            if proj in otherSysFile._projs:
                otbl = otherSysFile._projs[proj]
                self._projs[proj].updateValues( otbl )
            else:
                logging.debug("Other system file does not have project: %s"%proj)
        if autosave: self.save()
    
    
    def __cleanName(self, secname):
        global SEC_NAME
        if SEC_NAME.search( secname ) is not None:
            return SEC_NAME.search(secname).groups()[0]
        else: return secname #TODO: fix this use case!!
        
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
                
        