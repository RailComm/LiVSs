#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""This is the core of the LiVSs system. It is configurable either by
command line options, or a LiVSs script. In either case, it takes a 
dictonary/Namespace. 

The LiVSs Runner is essentially a giant state machine that checks what
it needs to do over the things it CAN do based on what configurations were
passed in. To see all the configs possible check the README to see the 
command line interface, or lslib.base.file.lsscript for a complete
dump list of them all. (NOTE, not all might be implemented yet, so check
README first!)

Steps to adding a new 'parser' (a new sub-command):
1.) Add the command and arguments to livss.py 
2.) In lsscript.py add all the variable names, (make sure the 
    destinations in argparse match).
3.) Add the parser check in LSRunner.run().
4.) Add a check in LSRunner.__script() too.
5.) ???
6.) Profit!

"""
import logging
import os.path as opath
from lslib.util.argstr import * #@UnusedWildImport
from lslib.base.file.utility.lsscript import LSScript 

# All function specific imports are done in their separate functions. This is 
# to reduce the global namespace's clutter as well as how much information is 
# loaded in memory (as most functions are memory intensive)!

def _NOT_IMPLEMENTED_():
    print("I'm Sorry, this portion of LiVSs has not been written yet.")

class LSRunner:
    """Takes a dictionary of all configs to kickstart the system."""
    PRIVATE_VARS = ['subparser_name', 'subsubparser_name', 'script_save_path']
    NONE_DIR = '-'
    
    def __init__(self, cfgs):
        self.__cfgs = cfgs
        
    def __config(self, name, default=None):
        """To ease getting configurations out of internal dictionary."""
        return self.__cfgs.get(name, default)
    
    def __cfgexists(self, lst, all=False):
        count = 0
        for key in self.__cfg.keys():
            if key in lst: 
                count+=1
                if not all: break
        if all: return count == len(lst)
        else: return count > 0
    
    def __cfgmatch(self, startswith):
        for key in self.__cfgs.keys():
            if key.startswith(startswith): return True
        return False
           
    def __saveCfgs(self):
        """Some configuration variables need to be removed from the internal
        dictionary, before saving them.
        """
        import copy
        cfgs = copy.deepcopy(self.__cfgs)
        for var in LSRunner.PRIVATE_VARS: cfgs.pop(var, None)
        return cfgs
        
    def run(self):
        """This is the only function worth knowing about in LSRunner,
        it is what starts the whole system running.
        """
        logging.debug("RUNNING") ; logging.debug( self.__cfgs )
        ###############################################
        if self.__config('run_timer'):
            import time
            timer = time.time()
        try:
            if self.__config('subparser_name') == prsr_EXPORT:
                logging.debug("export subparser found")
                self.__export()
            elif self.__config('subparser_name') == prsr_UPDATE:
                self.__update()
            
            # Otherwise we are using a script, so we need to determine what we 
            # are doing the hard way.
            else: self.__script()
        except: raise
        #finally save the configs in a file, if wanted.
        if self.__config('script_save_path', False):
            script = LSScript(self.__config('script_save_path'))
            script.dumpCfgs(self.__saveCfgs())
            
        if self.__config('run_timer'):
            print("LiVSs took: %d seconds"%(time.time()- timer)) 
        ###############################################
        
###############################################################################
########################## UTILITY FUNCTIONS ##################################
###############################################################################
    
    def __script(self):
        logging.debug("Starting script...")
        export, update = [ False for _ in range(2) ]
        for var in self.__cfgs.keys():
            if var.startswith("export"): export = True
            elif var.startswith("update"): update = True
        lst = list(filter(lambda x: x, [export, update]))    
        
        # There are more than one function being asked to run. We
        # can't accurately determine which function should run first.
        if len(lst) > 1:
            raise Exception("Script is ambiguous, must return a single function.")
        
        # For each possibility 
        elif export: self.__export()
        elif update: self.__update()
        
        # There is no valid function described. It can't be run, so raise
        # an exception for the user to read.
        else: raise Exception("Script is not valid. Try using the command line.")


    def __update(self):
        logging.debug("Starting Update...")
        from lslib.pushing.push import Pusher, PusherInputs, PusherOutputs
        
        logging.debug("Checking I/O.")
        if not self.__update_verifyOutput(): 
            raise Exception("Output directory/file does not exist")
        
        outtype = self.__config('update_to', 'rcs')
        makenew = self.__config('update_new', False)
        isMenu  = self.__config('update_menus', False)
        isDlog  = self.__config('update_dialogs', False)
        isStrs  = self.__config('update_strings', False)
        isTrans = self.__config('update_translator', False)
        
        langcodes = self.__config('update_langcodes', None) 
        if langcodes == []: langcodes=None
        
        inPath  = list(filter(None,[isMenu, isDlog, isStrs, isTrans]))[0]
        outPath = self.__config('output') 
        
        pushInput = list(  # I was missing my Functional Programming...
                         map( (lambda x: x[0]), 
                              filter( (lambda x: x[1]), 
                                      zip( PusherInputs.LIST, 
                                           [isMenu, isDlog, isStrs, isTrans]))))[0]
        if outtype == 'sys':
            if opath.isdir(outPath):
                pushOutput = PusherOutputs.ALL_SYS_FILES
            elif opath.splitext(outPath)[1] == 'strtbls':
                pushOutput = PusherOutputs.SYS_STRTBL
            elif opath.splitext(outPath)[1] == 'menus':
                pushOutput = PusherOutputs.SYS_MENU
            elif opath.splitext(outPath)[1] == 'dialogs':
                pushOutput = PusherOutputs.SYS_DIALOG
            else: raise IOError("Invalid file given for selected `outtype`!")          
        elif outtype == 'proj':
            if opath.isdir(outPath):
                pushOutput = PusherOutputs.ALL_PROJ_FILES
                #TODO: There needs to be a way of selecting all of a particular file-type
                # ie, all string tables.
            elif opath.splitext(outPath)[1] == 'strtbls':
                pushOutput = PusherOutputs.PROJ_STRTBL
            elif opath.splitext(outPath)[1] == 'menus':
                pushOutput = PusherOutputs.PROJ_MENU
            elif opath.splitext(outPath)[1] == 'dialogs':
                pushOutput = PusherOutputs.PROJ_DIALOG
            else: raise IOError("Invalid file given for selected `outtype`!")
        else: #rcs
            if opath.isdir(outPath):
                pushOutput = PusherOutputs.ALL_RESOURCES
            else: pushOutput = PusherOutputs.RESOURCE
        
        pusher = Pusher( inPath, pushInput, 
                         outPath, pushOutput, 
                         langcodes, makenew )
        try:
            pusher.push() #TODO: get backup dir from cmd line?
        except IOError as e:
            print("There was an IO error when pushing back the files. Make sure the resources are not Read-only.")
            logging.exception(e)
        except Exception as e:
            logging.exception(e)
            print(e)    
            
        logging.debug("Finished Update...")
        
    
    def __export(self):
        logging.debug("Starting exporting...")
        from lslib.exporting.join import Joiner, JoinLevel
        util  = ( self.__config('subsubparsr_name','')=='util' or \
                  self.__cfgmatch('export_util') )
        trans = ( self.__config('subsubparsr_name','')=='translator' or \
                  self.__cfgmatch('export_translator') ) 
        
        # Check that input/output is valid
        logging.debug("Checking I/O.")
        if not self.__export_verifyInput():  raise Exception("Input directory is invalid")
        if not self.__export_verifyOutput(): raise Exception("Output directory is invalid")
        
        # Create the joiner which will be making our utilities or translators
        output = self.__config('output', None)
        if output == LSRunner.NONE_DIR: output = None
        joiner = Joiner(self.__config('input'), output)
        
        # Set the parser level details
        mem = self.__config('export_mem', False)
        useExists = self.__config('export_existing', False)
        defaultLevel = 'lang' if util else 'sys'
        level = JoinLevel.determineLevel( self.__config('export_level', defaultLevel) )
        
        # If we are finding the utility files, lets check which ones they want.
        if util:
            logging.debug("Creating UTILITIES...")
            
            # Set up joining configurations
            menu,dialog,strs = [False for _ in range(3)]
            if self.__config('export_util_menus',   False): menu = True
            if self.__config('export_util_dialogs', False): dialog = True
            if self.__config('export_util_strings', False): strs = True
            if self.__config('export_util_all', False): 
                menu,dialog,strs = True,True,True
            
            # now that we determined out joins levels, lets do it.
            try:
                if level == JoinLevel.LANG:
                    logging.debug("Starting Language level join.")
                    joiner.makeLangLevelUtil(doMenus=menu, doDialogs=dialog, doStrings=strs)
                elif level == JoinLevel.PROJ: 
                    logging.debug("Starting Project level join.")
                    joiner.makeProjLevelUtil(keepInMem=mem, doMenus=menu, doDialogs=dialog, 
                                             doStrings=strs)
                elif level == JoinLevel.SYS:
                    logging.debug("Starting System level join.")
                    joiner.makeSysLevelUtil(existing=useExists, keepInMem=mem, doMenus=menu, 
                                            doDialogs=dialog, doStrings=strs)
                else: raise Exception("Invalid level selection for exporting.")
            except: raise 
            
        if trans: 
            logging.debug("Creating TRANSLATOR...")
            langcodes = self.__config('export_translator_langcodes', None)
            ordr = self.__config('export_translator_order', False)
            ppath = self.__config('export_translator_prunepath', None)
            conflicts = self.__config('export_translator_markconflicts', False)
            joiner.makeTranslator( langcodes, existing=useExists, keepInMem=mem, 
                                   order=ordr, prunepath=ppath, markconflicts=conflicts)
            
        logging.debug("Finished exporting...")


    def __export_verifyInput(self):
        """ input must be a directory. """
        return opath.isdir( self.__config('input') )
    
    def __update_verifyOutput(self):
        return opath.exists( self.__config('output') )
    
    def __export_verifyOutput(self):
        """ output must be a directory, or None, or '-' """
        if self.__config('output', None) is None or \
           self.__config('output', None) == '-': return True
        return opath.isdir( self.__config('output') )
    