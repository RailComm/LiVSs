#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""On base utility dialog files sections are described like [dialogid], 
however in System level dialog files, the sections are: 
                        [project name.dialogid] 
So all we'd have to do is parse for the 'dot' and we'd have the project 
name and the ID of the dialog. This makes it simple to parse out which 
sections are for which project and we still maintain the dialog state.

All parsing of this file type happens in the SysDialogFile object, and 
shouldn't be moved as there is no need to delve much deeper than what 
functions are provided via the BaseUtilityFileWrapper object. Any 
accessors can be pushed to a per-project level.
"""

import copy
from lslib.base.file.lscsv              import LSCSV
from lslib.base.file.msrcobj.dialogex   import RCDialog
from lslib.base.file.utility.DialogFile import RCDialogFile, InMemDialog
from lslib.base.file.msrcobj.msobjbase  import RCStringValue
from lslib.base.file.syslvl.sysbase     import BaseUtilityFileWrapper, \
                                               isSystemLevelDialog

class SysDialogFile( BaseUtilityFileWrapper, LSCSV ):
    """This is the object that allows you to pull individual projects' dialog
    files in and out of the master System Dialog Files. To utilize it, just 
    give it a path name of the system file and call load.
    """
    def __init__(self, path): 
        if not isSystemLevelDialog( path ):
            raise TypeError("Path given is not a system level dialog file.")
        super().__init__( path )
        self.setHasSections( True )
        self._projs = {} #map: "projName" -> [RCDialogs]
        
    def load(self, newpath=None):
        if newpath is not None:
            if not isSystemLevelDialog( newpath ):
                raise TypeError("Path given is not a system level dialog file.")
            else: self._path = newpath
        self._projs = {}
        offset = RCDialogFile.CONTROL_COLS
        header = self.getHeader( RCDialogFile.HEADER_ROW )
        langcodes = len(header)-offset;
        sections = self.readSection()
        for secname, entries in sections:
            name, lid = self.__splitSectionName(secname)
            if name not in self._projs: self._projs[name]=[]
            dialog = RCDialog(lid)
            for entry in entries:
                value = RCStringValue(entry[0]) #id
                for c in range(langcodes):
                    value.addValuePair(header[offset+c], entry[offset+c])
                dialog._values.append(value)
            self._projs[name].append( dialog )
        self.__loaded = True
        
    def save(self, newpath=None):
        # we don't care about checking if its syslvl, we are overwriting.
        if newpath is not None: self._path = newpath
        #create header:
        lst = {}
        for dialogs in self._projs.values():
            for dialog in dialogs:
                for l in dialog.getPossibleLangs(): lst[l]=1
        langorder = list(lst.keys())
        header = RCDialogFile.HEADER_COLS+langorder
        sections = {}
        #generate sections
        for name, dialogs in self._projs.items():
            for dialog in dialogs:
                section = "%s.%s"%(name,dialog.id)
                sections[section] = self.__buildLines(dialog, langorder)
        #write sections
        writer = self.writeLine( header )
        self.writeSections(sections, writer)
        
    def getProjectList(self):
        return list(self._projs.keys())
        
    def removeProjLevelFile(self, projName):
        return self._projs.pop(projName, None) is not None
    
    def addProjLevelFile(self, projName, path, obj=None, overwrite=True): 
        if not overwrite and projName in self._projs:
            raise KeyError("Project already exists!")
        if obj is None:
            file = RCDialogFile( path )
            if not file.load():
                raise Exception("Could not load Dialog File: %s"%path)
        else: file = obj
        self._projs[projName] = copy.deepcopy(file._dialogs)
        return True
        
    def genProjLevelFile(self, projName, newPath, autosave=False): 
        if projName not in self._projs:
            raise KeyError("Project wasn't found in the system file.")
        file = InMemDialog( newPath, self._projs[projName] )
        if autosave: file.save()
        return file
    
    
    def updateFromTranslation(self, otherSysFile, autosave=False):
        for proj in self._projs.keys():
            odlogs = otherSysFile._projs[proj]
            for index in range(len(self._projs[proj])):
                # for each dialog in self, find it in the other file
                # and update it with the values in that one.    
                for odlog in odlogs:
                    if self._projs[proj][index].id == odlog.id:
                        self._projs[proj][index].updateValues( odlog )
                        break
        if autosave: self.save()
    
    
    def __buildLines(self, dialog, langorder):
        ### Builds a 2D list of lists that are the entries for saving the 
        ### given dialog.
        if len(langorder) == 0: return []
        lines = []
        for entry in dialog._values:
            line = [entry.getID()]
            for lang in langorder:
                line.append(entry.getValue(lang,''))
            lines.append(line)        
        return lines
        
    def __splitSectionName(self, header):
        try:
            name, lid = header.split(".",1)
            return name, lid
        except: return header, header #TODO: fix this use case!!
        