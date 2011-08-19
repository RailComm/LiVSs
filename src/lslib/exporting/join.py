#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""Joining files is similar to pushing, but both datasets are maintained and 
just the format is different. An example of this is to take two resource
files and pushing them into one csv file, or taking several csv files and
pushing them into a single Excel xlsx file.

In LiVSs we have lots of possibilities to join together, we have all of our
utility files, resource files, translation files, system level files, etc. 
There are options for each; but some need more coercion to get to a different
file type than others. 

Here are the possibilities, if there is an intermediate step to get to the 
other file, it will say so. Also, its broken up by levels: Language level 
(only one resource file for one project), Project level (one or more 
resource files for a single project), System level (one or more resource files
each for one or more projects). The higher the level, the more intermediate 
steps.

=File Joins:=

--Language Level:--
    - Resource -> Menu File
    - Resource -> Dialog File
    - Resource -> String Table File
    - Resource -> Translation File [1]
        * generates all utility files first
    - Menu File -> Translation File  [1]
    - Dialog File -> Translation File [1]
    - String Table File -> Translation File [1]

--Project Level:--
    - All Project Resources -> Menu File
    - All Project Resources -> Dialog File
    - All Project Resources -> String Table File
    - All Project Resources -> Translation File  [1]
        * generates all utility files first
    - Menu File -> Translation File  [1]
    - Dialog File -> Translation File  [1]
    - String Table File -> Translation File  [1]
    
--System Level:--
    - All Projects -> System Menu File
        * generates all project level menu files first
    - All Projects -> System Dialog File
        * generates all project level dialog files first
    - All Projects -> System String Table File
        * generates all project level String Table files first
    - All Projects -> System Translation File
        * generates all sys-lvl Utility files first
    - System Menu File -> System Translation File
    - System Dialog File -> System Translation File
    - System String Table File -> System Translation File
    - All System Utility Files -> System Translation File 
    
 [1] - There is only one kind of translation file, so there is no difference
     between system wide, project wide, or a single language. This means a
     System level utiliy file is needed to generate the translation file. So
     in most instances (if its not given as input) the system file will be 
     generated IN MEMORY to be passed to the joiner function for the 
     translation file.
     
For each intermediate step, it can write the files to disk, or just store it 
in memory. This, however, is not recommended when running trying to create
a System level Translation file. (example: on our system at the time of this
writing would need to store over 3000 files in memory to pull this off!) 

A few warnings:
- It is assumed you want the Lang-lvl and Project-lvl utility files in the 
same directory as the resource file is found. System-lvl files will always be
generated in the top level directory that was given to the Joiner as input to
search in.
    - However you can change this assumption by changing the output directory
      This will not differentiate where each lvl is saved (i.e., all files
      generated will be placed in that directory, even ones from different
      levels).
  
- There is a difference between System level files and all others, as they are
  joins of other projects and must hold the data differently to maintain 
  project differences.
  
- Language and project level files are pretty much the exact same, except that
  they may be named differently. Lang level files are normally the same name
  as the resource they represent except with a different extension (i.e., 
  UserInterface_1033.menus), whereas Project level files are named after the 
  project they are for (i.e., User Interface.menus).
  
    - Because of this it is possible to have the same name for both project
      and language level files. In this event, assume it is Project level, as
      that is what holds the most information and is generally more useful. 
      For these reasons LiVSs defaults to this case resolution.
"""

import logging
import os.path as opath
import lslib.util.iohelp as iohelp

from lslib.exporting.merges import ScanAndMergeMenus,   \
                                   ScanAndMergeDialogs, \
                                   ScanAndMergeStrings

from lslib.base.file.rcsfile import scanRCFile
from lslib.base.file.utility.MenuFile import RCMenuFile, InMemMenu
from lslib.base.file.utility.DialogFile import RCDialogFile, InMemDialog
from lslib.base.file.utility.StrTblFile import RCStrTblFile, InMemTable
from lslib.base.file.utility.TranslationFile import MakeTranslationFile 

from lslib.base.file.syslvl.SysMenuFile   import SysMenuFile
from lslib.base.file.syslvl.SysDialogFile import SysDialogFile 
from lslib.base.file.syslvl.SysStrTblFile import SysStrTblFile

class JoinLevel():
    """Defines the level at which the joins should take place. There are only
    three levels: Language, Project, and System. See the above description for 
    more information of what each level represents and the joins that can take
    place at each level.
    """
    LANG, PROJ, SYS, DERIVED = range(4)
    
    @staticmethod
    def determineLevel( s ):
        if type(s) is str:
            if s=='lang': return JoinLevel.LANG
            elif s=='proj': return JoinLevel.PROJ
            elif s=='sys': return JoinLevel.SYS
        elif type(s) is int: return s
        return JoinLevel.DERIVED  
            
    
class Joiner():
    """The joiner class can be created by passing in the path to your system. 
    That means the top level directory that leads to a list of your projects,
    another word for the system directory would perhaps be the source or 
    solution directory.
    """
    
    MASTER_FILENAME = "System_Strings.master"
    TRANS_FILENAME  = "MasterTranslationFile.xls"
    
    def __init__(self, sysDir, output=None): 
        if opath.isdir(sysDir):
            self.__sysdir = opath.dirname(sysDir)
        else: raise TypeError("Given path is not a valid directory.")
        self.__changeoutputs = (output is not None)
        if self.__changeoutputs: 
            if opath.isdir(output):
                self.__outdir = opath.dirname(output)
            else: raise TypeError("Given path is not a valid directory.")
            

    @staticmethod
    def makeSysDialog( projDialogFiles, sysDialogPath, autosave=True ): 
        """Passing in a list of paths to dialog files, and a path for the new
        System level dialog file, this function will join all of them into 
        a new Master dialog file for your entire solution.
        """
        sdf = SysDialogFile( sysDialogPath )
        for file in projDialogFiles:
            name = iohelp.lastdirname(file)
            try:
                sdf.addProjLevelFile(name, file)
            except Exception as e: logging.exception(e)
        if autosave: sdf.save()
        return sdf
    
    @staticmethod
    def makeSysMenu( projMenuFiles, sysMenuPath, autosave=True  ): 
        """Passing in a list of paths to menu files, and a path for the new 
        System level menu file, this function will join all of them into a 
        new Master menu file for your entire solution.
        """
        smf = SysMenuFile(sysMenuPath)
        for file in projMenuFiles:
            name = iohelp.lastdirname(file)
            try:
                smf.addProjLevelFile(name, file)
            except Exception as e: logging.exception(e)
        if autosave: smf.save()
        return smf
    
    @staticmethod 
    def makeSysStrTbl( projStrTblFiles, sysStrTblPath, autosave=True  ):
        """Passing in a list of paths to string table files, and a path for a 
        new System level string table file, this function will join all of
        them into a new Master string table file for your entire solution.
        """  
        ssf = SysStrTblFile(sysStrTblPath)
        for file in projStrTblFiles:
            name = iohelp.lastdirname(file)
            try:
                ssf.addProjLevelFile(name, file)
            except Exception as e: logging.exception(e)
        if autosave: ssf.save()
        return ssf

    
    def makeLangLevelUtil(self, doMenus=True, doDialogs=True, doStrings=True):
        """Since the underbelly of Joiner is itterative, generators are used. This 
        function hides all of the mess and lets you just call the function directly.
        """
        try:
            for _ in self.__genLangLevelUtil(False, True, doMenus, doDialogs, doStrings): pass
        except: raise
    
    def makeProjLevelUtil(self, keepInMem=False, doMenus=True, doDialogs=True, doStrings=True):
        """Since the underbelly of Joiner is itterative, generators are used. This 
        function hides all of the mess and lets you just call the function directly.
        """
        try:
            for _ in self.__genProjLevelUtil(False, keepInMem, False, True, doMenus, doDialogs, doStrings): pass
        except: raise
    
    def makeSysLevelUtil(self, existing=False, keepInMem=False, doMenus=True, doDialogs=True, doStrings=True):
        """Since the underbelly of Joiner is itterative, generators are used. This 
        function hides all of the mess and lets you just call the function directly.
        """
        try: _ = self.__genSysLevelUtil(existing, existing, keepInMem, True, doMenus, doDialogs, doStrings)
        except: raise
    
    def makeTranslator(self, langcodes, existing=False, keepInMem=False, order=False, prunepath=None, markconflicts=False):
        """Since the underbelly of Joiner is itterative, generators are used. This
        function hides all of the mess and lets you just call the function directly.
        """
        _ = self.__genTranslator(langcodes, existing, keepInMem, True, False, order, prunepath, markconflicts)
        

    def __genLangLevelUtil( self, ret=False, save=True, doMenus=True, doDialogs=True, doStrings=True): 
        """Generate the Language Level utility files for the entire system."""
        for cpath,name in iohelp.dirwalk(self.__sysdir, filter=iohelp.RCFilters.RCFilter, ignore=iohelp.RCFilters.BinaryDirs):
            logging.debug("~ LangLevel: found filter match '%s'! "%cpath)
            rcs = scanRCFile( cpath )
            if rcs is None: continue
            blank,_ = opath.splitext(cpath)
            totalMenus, totalDialogs, totalStrings = [],[],None
            if doMenus:
                menus = rcs.pullMenu()
                for menu in menus: totalMenus.append(menu)
                if save: 
                    #logging.debug("~ LangLevel: Saving menu file for resource '%s'! "%name)
                    if not self.__changeoutputs: InMemMenu(blank+".menus", totalMenus).save()
                    else: InMemMenu('', totalMenus).save(opath.join(self.__outdir, name+".menus"))
            if doDialogs:
                dialogs = rcs.pullDialog()
                for dialog in dialogs: totalDialogs.append(dialog)
                if save: 
                    #logging.debug("~ LangLevel: Saving dialog file for resource '%s'! "%name)
                    if not self.__changeoutputs: InMemDialog(blank+".dialogs", totalDialogs).save()
                    else: InMemDialog('', totalDialogs).save(opath.join(self.__outdir, name+".dialogs"))
            if doStrings:
                strings = rcs.pullStringTable()
                for table in strings:
                    if totalStrings is None: totalStrings=table
                    else: totalStrings.addStringTable( table )
                if save: 
                    #logging.debug("~ LangLevel: Saving string file for resource '%s'! "%name)
                    if not self.__changeoutputs: InMemTable(blank+".strtbls", totalStrings).save()
                    else: InMemTable('', totalStrings).save(opath.join(self.__outdir, name+".strtbls"))
            if ret: yield (cpath, totalMenus, totalDialogs, totalStrings)
               
    def __genProjLevelUtil( self, useExisting=False, keepInMem=False, ret=False, save=True, doMenus=True, doDialogs=True, doStrings=True ): 
        """Generate the Project Level Utility files for an entire system. If 
        `useExisting` has been set to True, it will use the existing utility 
        files for generating the project files. Otherwise it will regenerate
        new lang-level files (ie, overwrite existing). If `keepInMem` is True,
        it wont overwrite existing files, instead it will generate the new
        files and keep them in memory for the project level creation and then
        discard them.
        """
        menuFiles, dialogFiles, stringFiles = [],[],[] #our lang files
        projMenus, projDialogs, projStrings = None,None,None
        if not useExisting:
            project = ''
            basename=''
            for cpath, ms, ds, ss in self.__genLangLevelUtil(True, (not keepInMem), doMenus, doDialogs, doStrings):
                
                # if we arrive at a new project directory
                if iohelp.lastdirname(cpath) != project:
                    
                    #check first if we have any utility files from the previous 
                    #project we visited. If we do we need to create the project
                    #level files from them.
                    if len(menuFiles)>0 or len(dialogFiles)>0 or len(stringFiles)>0:
                        try:
                            if doMenus:
                                projMenus  = ScanAndMergeMenus( basename+".menus", menuFiles )
                            if doDialogs:
                                projDialogs = ScanAndMergeDialogs(basename+".dialogs", dialogFiles )
                            if doStrings:
                                projStrings = ScanAndMergeStrings(basename+".strtbls", stringFiles )
                            if save:
                                if doMenus: 
                                    if not self.__changeoutputs: projMenus.save()
                                    else: projMenus.save(opath.join(self.__outdir, project+".menus"))
                                if doDialogs: 
                                    if not self.__changeoutputs: projDialogs.save()
                                    else: projDialogs.save(opath.join(self.__outdir, project+".dialogs"))
                                if doStrings: 
                                    if not self.__changeoutputs: projStrings.save()
                                    else: projStrings.save(opath.join(self.__outdir, project+".strtbls"))
                            if ret: 
                                yield project, projMenus, projDialogs, projStrings
                        except Exception as e: logging.exception(e)
                    # now that we have all the previous project stuff set up, lets
                    #reset our project vars with the current information.
                    project = iohelp.lastdirname( cpath )
                    basename = opath.join( opath.dirname(cpath), project )
                    menuFiles, dialogFiles, stringFiles = [],[],[]
                       
                # Add our lang-level utility files to their respective lists. 
                blank,_ = opath.splitext( cpath )
                if doMenus:   menuFiles   .append( InMemMenu(blank+".menus", ms)    )
                if doDialogs: dialogFiles .append( InMemDialog(blank+".dialogs", ds))
                if doStrings: stringFiles .append( InMemTable(blank+".strtbls", ss) )
                
            #We are out of the iteration. Lets check if we finished in the middle
            #of a project (which is highly likely).
            if len(menuFiles)>0 or len(dialogFiles)>0 or len(stringFiles)>0:
                project  = iohelp.lastdirname( cpath )
                basename = opath.join( opath.dirname(cpath), project )
                if doMenus:   projMenus   = ScanAndMergeMenus( basename+".menus", menuFiles )
                if doDialogs: projDialogs = ScanAndMergeDialogs(basename+".dialogs", dialogFiles )
                if doStrings: projStrings = ScanAndMergeStrings(basename+".strtbls", stringFiles )
                if save:
                    if doMenus: 
                        if not self.__changeoutputs: projMenus.save()
                        else: projMenus.save(opath.join(self.__outdir, project+".menus"))
                    if doDialogs: 
                        if not self.__changeoutputs: projDialogs.save()
                        else: projDialogs.save(opath.join(self.__outdir, project+".dialogs"))
                    if doStrings: 
                        if not self.__changeoutputs: projStrings.save()
                        else: projStrings.save(opath.join(self.__outdir, project+".strtbls"))
                if ret: yield project, projMenus, projDialogs, projStrings
        else: #itterate through existing.
            #Loop through all the projects, and grab the utiliy files currently in
            #the directories.
            for utils in iohelp.dirwalkl(self.__sysdir,
                                          exclude=iohelp.RCFilters.SysLevelFilter, 
                                          filter=iohelp.RCFilters.UtilityFilter,
                                          ignore=iohelp.RCFilters.BinaryDirs):
                #for each utility file found, determine if its a dialog, menu, or stringtable
                #depending on which one we must add it to the correct list.
                for cpath, name in utils:
                    if iohelp.fileok(name, filter=["menus"]):
                        if not doMenus: continue
                        tmp = RCMenuFile(blank+".menus")
                        tmp.load()
                        menuFiles.append( tmp )
                    elif iohelp.fileok(name, filter=["dialogs"]):
                        if not doDialogs: continue
                        tmp = RCDialogFile(blank+".dialogs")
                        tmp.load()
                        dialogFiles.append( tmp  )
                    elif iohelp.fileok(name, filter=["strtbls"]):
                        if not doStrings: continue
                        tmp = RCStrTblFile(blank+".strtbls")
                        tmp.load()
                        stringFiles.append( tmp )
                    else: logging.error("Matched utility filter when there was no need! %s"%cpath)
                if len(menuFiles)>0 or len(dialogFiles)>0 or len(stringFiles)>0:
                    if doMenus:   projMenus   = ScanAndMergeMenus( basename+".menus", menuFiles )
                    if doDialogs: projDialogs = ScanAndMergeDialogs( basename+".dialogs", dialogFiles )
                    if doStrings: projStrings = ScanAndMergeStrings( basename+".strtbls", stringFiles )
                    if save:
                        if doMenus: 
                            if not self.__changeoutputs: projMenus.save()
                            else: projMenus.save(opath.join(self.__outdir, project+".menus"))
                        if doDialogs: 
                            if not self.__changeoutputs: projDialogs.save()
                            else: projDialogs.save(opath.join(self.__outdir, project+".dialogs"))
                        if doStrings: 
                            if not self.__changeoutputs: projStrings.save()
                            else: projStrings.save(opath.join(self.__outdir, project+".strtbls"))
                    if ret: yield project, projMenus, projDialogs, projStrings
                menuFiles, dialogFiles, stringFiles = [],[],[]
                basename = opath.join( opath.dirname(cpath), project )
                  
    def __genSysLevelUtil( self, useExisting=False, useExistingLangLevel=False, keepInMem=False, save=True, doMenus=True, doDialogs=True, doStrings=True ): 
        """Generate the System Level Utility files for an entire system. If 
        `useExisting` has been set to True, it will use the existing project 
        level utility files for generating the system level. Otherwise it will 
        regenerate new project level files (ie, overwrite existing). If 
        `keepInMem` is True, it wont overwrite existing files, instead it will 
        generate the new files and keep them in memory for the system level 
        creation and then discard them.
        """
        if self.__changeoutputs:
            basename = opath.join(self.__outdir, Joiner.MASTER_FILENAME)
        else:
            basename = opath.join(self.__sysdir, Joiner.MASTER_FILENAME)
        sysMenus   = SysMenuFile(basename+".menus")
        sysDialogs = SysDialogFile(basename+".dialogs")
        sysStrings = SysStrTblFile(basename+".strtbls")
        if not useExisting:
            for project, menuFile, dialogFile, stringFile in self.__genProjLevelUtil(useExistingLangLevel,
                                                                          keepInMem, True, useExisting,
                                                                          doMenus, doDialogs, doStrings):
                if doMenus:   sysMenus.addProjLevelFile(project, '', obj=menuFile)
                if doDialogs: sysDialogs.addProjLevelFile(project, '', obj=dialogFile)
                if doStrings: sysStrings.addProjLevelFile(project, '', obj=stringFile)
        else: # iterate through 
            # Since we can't generate new ones, we have to go look for them in subdirs.
            # Also since we are looking through the subdirs, we run the risk of pulling out
            # lang-level utility files. So we need to prune those too.
            for utils in iohelp.dirwalkl(self.__sysdir, 
                                          exclude=iohelp.RCFilters.SysLevelFilter, 
                                          filter=iohelp.RCFilters.UtilityFilter, 
                                          ignore=iohelp.RCFilters.BinaryDirs):
                strFound, menuFound, dialogFound = False, False, False
                # we have all the util files for the project.
                for cpath,name in utils:
                    project = iohelp.lastdirname( cpath )
                    # if file is lang-lvl, then skip it.
                    if opath.splitext(name)[0] != project: 
                        logging.debug("thought was lang-lvl: %s,%s"%(project, opath.splitext(name)[0]))
                        continue #TODO: not very elegant! plus is it true??
                    
                    logging.debug("filter time: %s"%name)
                    
                    if iohelp.fileok(name, filter=iohelp.RCFilters.MenuFilter):
                        menuFound = True
                        if not doMenus: continue
                        sysMenus.addProjLevelFile( project, cpath )
                    elif iohelp.fileok(name, filter=iohelp.RCFilters.DialogFilter):
                        dialogFound = True
                        if not doDialogs: continue
                        sysDialogs.addProjLevelFile( project, cpath )
                    elif  iohelp.fileok(name, filter=iohelp.RCFilters.StrTblFilter):
                        strFound = True
                        if not doStrings: continue
                        sysStrings.addProjLevelFile(project, cpath )
                    else: logging.error("Matched utility filter when there was no need! %s"%cpath)
                
                if not (strFound and menuFound and dialogFound):
                    logging.warning("Was unable to find all of %s's utility files."%project)
                    
        if save:
            if doMenus:   sysMenus.save()
            if doDialogs: sysDialogs.save()
            if doStrings: sysStrings.save()
        return sysMenus, sysDialogs, sysStrings 
        
    
    def __genTranslator( self, langcodes, useExisting=False, keepInMem=False, save=True, ret=False, order=False, prunepath=None, markconflicts=False ): 
        """Generate the translator file for the entire system."""
        if self.__changeoutputs:
            newpath = opath.join(self.__outdir, Joiner.TRANS_FILENAME)
        else: newpath = opath.join(self.__sysdir, Joiner.TRANS_FILENAME)
        
        if not useExisting:
            menuFile, dialogFile, stringFile = self.__genSysLevelUtil(useExisting=False, 
                                                                      useExistingLangLevel=False, 
                                                                      keepInMem=keepInMem, 
                                                                      save=False)
        else: #we must load by hand.
            basename = opath.join( self.__sysdir, Joiner.MASTER_FILENAME )
            menuFile   = SysMenuFile(basename+".menus")
            dialogFile = SysDialogFile(basename+".dialogs")
            stringFile = SysStrTblFile(basename+".strtbls")
            menuFile.load() ; dialogFile.load() ; stringFile.load()

        trans = MakeTranslationFile(newpath, menuFile, dialogFile, stringFile, True, save, langcodes, order, False, prunepath, markconflicts)
        if ret: return trans
        
        