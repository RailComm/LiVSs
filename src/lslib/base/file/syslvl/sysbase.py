#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""System Files are joins of all resources of 'like' files into one file that
holds all information for a part or entire system. This means the creation and
usage of master string tables, dialogs, and menus files.

System Files can be seen as wrappers or extractors for the basic utility files,
as they act and look pretty much the same as their per-Project level counter
parts. However, they must also hold project level distinguishing features to
aid in the joining and pushing process (too and from translator files).

In this file, we have the base wrapper and several functions for determining if
a file is a project level file or a system level file.
"""

import re
import os
from lslib.util.iohelp import ScanUntilMatch, ScanUntilNotMatch


def isSystemLevelMenu( menuFilePath ):
    """Checks a file if its a System menu file. If it is, it will return True.
    If it isn't, it will return False. If it is not even a menu file it will 
    raise a TypeError. 
    """
    sysMenuCheck = re.compile("^<SYSTEM")
    utilMenuCheck = re.compile("^<RCMENUS")
    if os.path.exists(menuFilePath):
        try:
            match = ScanUntilMatch(menuFilePath, sysMenuCheck)
            if match is None:
                match = ScanUntilMatch(menuFilePath, utilMenuCheck)
                if match is None: raise TypeError("Not a menu file: %s"%menuFilePath)
                else: return False
            return True
        except: raise #Explicit raise.
    else: return True
    
def isSystemLevelDialog( dialogFilePath ):
    """Checks a file if its a System dialog file. If it is, it will return 
    True. If it isn't, it will return False. If it is not even a dialog file 
    it will raise a TypeError. 
    """
    sysDialogCheck = re.compile("^\[.+\.[A-Z]{2,3}_[0-9A-Z_]+\](,?)*$")
    utilDialogCheck = re.compile("^\[[A-Z]{2,3}_[0-9A-Z_]+\](,?)*$")
    if os.path.exists(dialogFilePath):
        try:
            match = ScanUntilMatch(dialogFilePath, sysDialogCheck)
            if match is None:
                match = ScanUntilMatch(dialogFilePath, utilDialogCheck)
                if match is None: raise TypeError("Not a dialog file: %s"%dialogFilePath)
                else: return False
            return True
        except: raise #Explicit raise.
    else: return True
    
def isSystemLevelStringTable( strFilePath ): 
    """Checks a file if its a System string table file. If it is, it will 
    return True. If it isn't, it will return False. If it is not even a 
    string table file it will raise a TypeError. 
    """
    sysTableCheck = re.compile("^\[\[.*?\]\]$")
    utilTableCheck = re.compile("^(.*?,)+(.*?)$") #standard csv essentially...
    if os.path.exists(strFilePath):
        try:
            match = ScanUntilMatch(strFilePath, sysTableCheck)
            if match is None:
                match = ScanUntilNotMatch(strFilePath, utilTableCheck)
                if match is None: raise TypeError("Not a string table file: %s"%strFilePath)
                else: return False
            return True
        except: raise #Explicit raise.
    else: return True


class BaseUtilityFileWrapper():
    """The base functionality of a Utility wrapper. The three classes below 
    all implement this interface.
    """
    def size(self):
        """Gets the number of projects in the System file."""
        return len(self.getProjectList())
    
    def load(self, newpath=None):
        """Loads the file into memory."""
        raise NotImplementedError()
        
    def save(self, newpath=None): 
        """Saves the file into disc."""
        raise NotImplementedError()
    
    def hasProj(self, projName):  
        """Checks if a given project name is located in the sys file."""
        return projName in self.getProjectList()
    
    def getProjectList(self):  
        """Gets a list of the projects that have been loaded into the system 
        file."""
        raise NotImplementedError()
    
    def removeProjLevelFile(self, projName):  
        """Removes a project from the system file (useful if you want to backup
        only a given number of projects)."""
        raise NotImplementedError()
    
    def addProjLevelFile(self, projName, path, obj=None, overwrite=True):  
        """Adds a project to the system file via a name and a given path to the
        project level utility file."""
        raise NotImplementedError()
    
    def genProjLevelFile(self, projName, newPath, autosave=False):  
        """Generates a project level utility file via what's stored in the 
        System file. It returns the object pre-saved unless autosave is turned
        on. Then the objects `save` function is called before returning."""
        raise NotImplementedError()
    
    def updateFromTranslation(self, otherSysFile, autosave=False):
        """ Update current values, WILL NOT CHANGE STRUCTURE OR ADD ELEMENTS. 
        Merely for push-back. Assumes everything is lined up as it should. If a
        language code is missing in current file, it is able to add it. (ie, if
        current Sys file only has 1033 and 2058, adding 13322 is fine.)
        """
        raise NotImplementedError()