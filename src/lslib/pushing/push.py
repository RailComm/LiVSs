#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#

"""Pushing is undoubtedly easy now, since we have a bunch of parsers and reg-ex 
already developed. Most of the really hard work will be done by the files 
themselves.

However the Pusher class does two things: First it provides a lot of easy
to use functions for one-hit conversions, and second it holds the state of
both files and can reload the old files in the event of an error.

LATER:
    - It would be nice to be able to push back into utility files too..
"""
import logging
import os.path as opath

from lslib.util.iohelp import dirwalk, RCFilters
from lslib.base.file.rcsfile import scanRCFile

from lslib.base.file.utility.MenuFile   import RCMenuFile
from lslib.base.file.utility.DialogFile import RCDialogFile
from lslib.base.file.utility.StrTblFile import RCStrTblFile
from lslib.base.file.utility.TranslationFile import TranslationFile

from lslib.base.file.syslvl.SysMenuFile   import SysMenuFile                        
from lslib.base.file.syslvl.SysDialogFile import SysDialogFile                                           
from lslib.base.file.syslvl.SysStrTblFile import SysStrTblFile

from lslib.base.file.syslvl.sysbase import isSystemLevelMenu,     \
                                           isSystemLevelDialog,   \
                                           isSystemLevelStringTable

class PusherInputs:
    """ These are the types of inputs that can be pushed into other files.
    Notice that resources aren't on here because we can't resources into 
    anything, thats an export.
    """
    MENU, DIALOG, STRTBL, TRANS = range(4)
    LIST = [MENU, DIALOG, STRTBL, TRANS]
    
class PusherOutputs:
    """These are the types of outputs that can be pushed to from one of
    the `PusherInputs`. Notice that Translators aren't on here as they are
    something someone exports into. You can not update a translator file,
    only generate a new one.
    """
    ALL_RESOURCES, RESOURCE,                            \
    ALL_SYS_FILES, SYS_MENU, SYS_DIALOG, SYS_STRTBL,    \
    ALL_PROJ_FILES, ALL_PROJ_MENU, PROJ_MENU,           \
                    ALL_PROJ_DIALOG, PROJ_DIALOG,       \
                    ALL_PROJ_STRTBL, PROJ_STRTBL        = range(13)    
    @staticmethod 
    def isResource( id ): 
        return id == PusherOutputs.ALL_RESOURCES  \
            or id == PusherOutputs.RESOURCE
    @staticmethod
    def isSysFile( id ):
        return id >= PusherOutputs.ALL_SYS_FILES \
            or id <= PusherOutputs.SYS_STRTBL
    @staticmethod
    def isProjFile( id ):
        return id >= PusherOutputs.ALL_PROJ_FILES \
            or id <= PusherOutputs.PROJ_STRTBL
    @staticmethod
    def isSingleFile( id ):
        return id != PusherOutputs.ALL_RESOURCES   \
           and id != PusherOutputs.ALL_SYS_FILES   \
           and id != PusherOutputs.ALL_PROJ_FILES  \
           and id != PusherOutputs.ALL_PROJ_STRTBL \
           and id != PusherOutputs.ALL_PROJ_MENU   \
           and id != PusherOutputs.ALL_PROJ_DIALOG
    @staticmethod
    def Filter( id ):
        if PusherOutputs.isResource( id ):
            return RCFilters.RCFilter
        elif PusherOutputs.isProjFile( id ) or \
             PusherOutputs.isSysFile( id ):
            return RCFilters.UtilityFilter
        else: return None
    @staticmethod
    def isStringTable( id ):
        return id == PusherOutputs.ALL_SYS_FILES  \
            or id == PusherOutputs.ALL_PROJ_FILES \
            or id == PusherOutputs.SYS_STRTBL     \
            or id == PusherOutputs.PROJ_STRTBL
    @staticmethod
    def isMenu( id ):
        return id == PusherOutputs.ALL_SYS_FILES  \
            or id == PusherOutputs.ALL_PROJ_FILES \
            or id == PusherOutputs.SYS_MENU       \
            or id == PusherOutputs.PROJ_MENU
    @staticmethod
    def isDialog( id ):
        return id == PusherOutputs.ALL_SYS_FILES  \
            or id == PusherOutputs.ALL_PROJ_FILES \
            or id == PusherOutputs.SYS_DIALOG     \
            or id == PusherOutputs.PROJ_DIALOG 
              
class InvalidPushError( Exception ):
    """If there is an invalid push (e.g., pushing from a menu to a dialog
    file), then this error type will be raised.
    """
    def __init__(self, msg='Invalid push type'):
        super().__init__( msg )
            
class MissingLangCodeError( Exception ):
    """This error can happen when trying to push into a file of a language
    code that the input file does not have. This could potentially cause 
    problems if it were to overwrite with all blank data. So LiVSs 
    will return this error instead of breaking everything.
    """
    def __init__(self, msg='Input does not have the correct language code.'):
        super().__init__( msg )


class Pusher:
    """Class to make file updating easier. """
    
    def __init__(self, inputPath, inputType, outputPath, outputType, langcodes=None, makenew=False):
        self.__input = inputPath
        self.__inputType = inputType
        self.__outputType = outputType
        self.__makenew = makenew
        self.__output = []
        self.__langcodes = langcodes
        self.__outputPath = outputPath
        if makenew or PusherOutputs.isSingleFile( outputType ):
            self.__output.append( (outputPath, opath.split(outputPath)[1]))
        else:
            self.__output = \
                [ x for x in dirwalk( outputPath, 
                                      filter=PusherOutputs.Filter(outputType), 
                                      ignore=RCFilters.BinaryDirs ) ]

    def push(self, backupDir=None):
        if PusherOutputs.isResource(self.__outputType):
            if self.__makenew: 
                logging.warning("LiVSs cannot create brand new resource files for you. Yet!")
                return
            if self.__inputType == PusherInputs.MENU:     self.__m2r()
            elif self.__inputType == PusherInputs.DIALOG: self.__d2r()
            elif self.__inputType == PusherInputs.STRTBL: self.__s2r()
            elif self.__inputType == PusherInputs.TRANS:  self.__t2r()
            else: raise InvalidPushError()
        elif PusherOutputs.isSysFile(self.__outputType):
            if self.__inputType == PusherInputs.TRANS : self.__trans2sys()
            else: raise InvalidPushError()
        elif PusherOutputs.isProjFile(self.__outputType):
            raise NotImplementedError("Project File push-back has not been written yet. " + \
                                      "Please push directly to resources or to system level "+ \
                                      "files for back up.")
        logging.debug("Pushing Complete!")
    
    def __validLangcode(self, code):
        if self.__langcodes is None:
            return True
        else: return code in self.__langcodes
    
    def __defaultLangCode(self):
        try:
            if len(self.__langcodes) > 0:
                return self.__langcodes[0]
            else: return '1033'
        except: return '1033'
    
    def __m2r(self): 
        logging.debug("Pushing menus into resources...")
        if isSystemLevelMenu(self.__input):
            logging.debug("\tMenus file is System Level.")
            file = SysMenuFile( self.__input )
            file.load()
            for cpath,name in self.__output:
                resource = scanRCFile(cpath)
                if not self.__validLangcode(resource._langcode):
                    logging.debug("\t\tIgnoring '%s' because its not the right langcode. @> %s"%(name,cpath)) 
                    continue
                try:
                    projFile = file.genProjLevelFile( resource._name, '' )
                except KeyError:
                    logging.warning("Project %s does not exist in %s"%(resource._name, self.__input))
                    continue
                logging.debug("\t\tUpdating %s @> %s"%(name,cpath))
                resource.updateMenus(projFile)
                
        else:
            logging.debug("\tMenus file is Project or language Level.")
            projFile = RCMenuFile( self.__input )
            projFile.load()
            langs = projFile._table.getPossibleLangs()
            for cpath,name in self.__output:
                resource = scanRCFile(cpath)
                if not self.__validLangcode(resource._langcode): 
                    logging.debug("\t\tIgnoring '%s' because its not the right langcode. @> %s"%(name,cpath)) 
                    continue
                if resource._langcode in langs:
                    logging.debug("\t\tUpdating %s @> %s"%(name,cpath))
                    resource.updateMenus(projFile)
                else: raise MissingLangCodeError()  

    def __d2r(self): 
        logging.debug("Pushing dialogs into resources...")
        if isSystemLevelDialog(self.__input):
            logging.debug("\tDialogs file is System level.")
            file = SysDialogFile( self.__input )
            file.load()
            for cpath,name in self.__output:
                resource = scanRCFile(cpath)
                if not self.__validLangcode(resource._langcode): 
                    logging.debug("\t\tIgnoring '%s' because its not the right langcode. @> %s"%(name,cpath)) 
                    continue
                try:
                    projFile = file.genProjLevelFile( resource._name, '' )
                except KeyError:
                    logging.warning("Project %s does not exist in %s"%(resource._name, self.__input))
                    continue
                resource.updateDialogs(projFile)
        else:
            logging.debug("\tDialogs file is Project or language Level.")
            projFile = RCDialogFile( self.__input )
            projFile.load()
            langs = projFile._table.getPossibleLangs()
            for cpath,name in self.__output:
                resource = scanRCFile(cpath)
                if not self.__validLangcode(resource._langcode): 
                    logging.debug("\t\tIgnoring '%s' because its not the right langcode. @> %s"%(name,cpath)) 
                    continue
                if resource._langcode in langs: 
                    logging.debug("\t\tUpdating %s @> %s"%(name,cpath))
                    resource.updateDialogs(projFile)
                else: raise MissingLangCodeError()  
    
    def __s2r(self): 
        logging.debug("Pushing strings into resources...")
        if isSystemLevelStringTable(self.__input):
            logging.debug("\tString table file is System Level.")
            file = SysStrTblFile( self.__input )
            file.load()
            for cpath,name in self.__output:
                resource = scanRCFile(cpath)
                if not self.__validLangcode(resource._langcode): 
                    logging.debug("\t\tIgnoring '%s' because its not the right langcode. @> %s"%(name,cpath)) 
                    continue
                try:
                    projFile = file.genProjLevelFile( resource._name, '' )
                except KeyError:
                    logging.warning("Project %s does not exist in %s"%(resource._name, self.__input))
                    continue
                resource.updateStringTables(projFile)
        else:
            logging.debug("\tString Table File is Project or Language Level.")
            projFile = RCStrTblFile( self.__input )
            projFile.load()
            langs = projFile._table.getPossibleLangs()
            for cpath,name in self.__output:
                resource = scanRCFile(cpath)
                if not self.__validLangcode(resource._langcode): 
                    logging.debug("\t\tIgnoring '%s' because its not the right langcode. @> %s"%(name,cpath)) 
                    continue
                if resource._langcode in langs: 
                    logging.debug("\t\tUpdating %s @> %s"%(name,cpath))
                    resource.updateStringTables(projFile)
                else: raise MissingLangCodeError()        
    
    def __t2r(self):
        logging.debug("Pushing Translator into resources...")
        trans = TranslationFile( self.__input, self.__defaultLangCode() )
        trans.load()
        logging.debug("\tPulling out sys utils")
        menuFile = trans.getSysMenuFile('')
        dlogFile = trans.getSysDialogFile('')
        strsFile = trans.getSysStrTblFile('')
        projFiles = {}
        for cpath,name in self.__output:
            resource = scanRCFile( cpath )
            if not self.__validLangcode( resource._langcode ): 
                logging.debug("\t\tIgnoring '%s' because its not the right langcode. @> %s"%(name,cpath)) 
                continue
            
            try:
                if resource._name in projFiles:
                    logging.debug("\t\tReloading proj lvl files for %s..."%resource._name)
                    projMenus, projDlogs, projConts = projFiles[ resource._name ]
                else:
                    logging.debug("\t\tPulling out proj lvl files for %s..."%resource._name)
                    projMenus = menuFile.genProjLevelFile(resource._name, '')
                    projDlogs = dlogFile.genProjLevelFile(resource._name, '')
                    projConts = strsFile.genProjLevelFile(resource._name, '')
                    projFiles[ resource._name ] = (projMenus, projDlogs, projConts)
            except KeyError:
                logging.warning("Project %s does not exist in %s. (path=%s,name=%s)"%(resource._name,self.__input,cpath,name))
                continue
            
            logging.debug("\t\tUpdating %s @> %s"%(name,cpath))
            buff = resource.updateMenus( projMenus, save=False )
            buff = resource.updateDialogs( projDlogs, save=False, buffer=buff )
            resource.updateStringTables( projConts, buffer=buff )
            
    def __trans2sys(self):
        logging.debug("Pushing Translator into System Level Utilities...")
        trans = TranslationFile( self.__input, self.__defaultLangCode() )
        trans.load()
        if self.__makenew:
            logging.debug("\tPulling out new sys utils")
            trans.getSysMenuFile( opath.join(self.__outputPath, "System_Strings.master.menus"), True, self.__langcodes )
            trans.getSysDialogFile( opath.join(self.__outputPath, "System_Strings.master.dialogs"), True, self.__langcodes )
            trans.getSysStrTblFile( opath.join(self.__outputPath, "System_Strings.master.strtbls"), True, self.__langcodes )
            logging.debug("\tSaved new system files from translator!")
            return
        
        logging.debug("\tPulling new sys utils to merge")
        menuFile = trans.getSysMenuFile('')
        dlogFile = trans.getSysDialogFile('')
        strsFile = trans.getSysStrTblFile('')
        strtbl, menus, dlogs = False, False, False
        
        for cpath,_ in self.__output:
            if opath.splitext(cpath)[1] == "strtbls" and \
               PusherOutputs.isStringTable( self.__outputType ):
                
                if strtbl: #only allow one?
                    logging.warning("\tFound another system string table file. Skipping: %s"%cpath)
                    continue
                tmp = SysStrTblFile(cpath)
                tmp.load()
                logging.debug("\tUpdating @> %s"%cpath)
                tmp.updateFromTranslation(strsFile, autosave=True)
                strtbl = True
                
            elif opath.splitext(cpath)[1] == "menus" and \
               PusherOutputs.isMenu( self.__outputType ):
                
                if menus: #only allow one?
                    logging.warning("\tFound another system menu file. Skipping: %s"%cpath)
                    continue
                tmp = SysMenuFile(cpath)
                tmp.load()
                logging.debug("\tUpdating @> %s"%cpath)
                tmp.updateFromTranslation(menuFile, autosave=True)
                menus = True
                
            elif opath.splitext(cpath)[1] == "dialogs" and \
               PusherOutputs.isDialog( self.__outputType ):
                
                if dlogs:  #only allow one?
                    logging.warning("\tFound another system dialog file. Skipping: %s"%cpath)
                    continue
                tmp = SysDialogFile(cpath)
                tmp.load()
                logging.debug("\tUpdating @> %s"%cpath)
                tmp.updateFromTranslation(dlogFile, autosave=True)
                dlogs = True
                
        # after we're done, lets inform them if there was something missing.
        if not strtbl: logging.debug("\tCould not find system string table file!")
        if not dlogs: logging.debug("\tCould not find system dialog file!")
        if not menus: logging.debug("\tCould not find system menu file!")
        