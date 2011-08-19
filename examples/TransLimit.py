#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""Removes projects from a translation file and then saves it as a new file.
"""

from lslib.base.file.utility.TranslationFile import TranslationFile
from lslib.base.file.syslvl.SysMenuFileCSV   import ConvertMenuXML2CSV


TRANS_PATH = "" #TODO: SET TO PATH OF XLS TRANSLATOR FILE
NEW_TRANS_PATH = "" #TODO: SET TO NEW PATH FOR FILTERED TRANSLATOR FILE

PRIMARY_LANGCODE = '1033'
PROJ_NAMES_TO_REMOVE = \
[
    #TODO: ADD NAMES OF PROJECTS HERE
]

if __name__ == "__main__":
    trans = TranslationFile(TRANS_PATH,PRIMARY_LANGCODE)
    newTrans = TranslationFile(NEW_TRANS_PATH,PRIMARY_LANGCODE)
    print("Loading translator...")
    trans.load()
    
    print("Extracting dialogs to filter...")
    newDlogs = trans.getSysDialogFile('')
    print("Extracting string tables to filter...")
    newStrTbl = trans.getSysStrTblFile('')
    print("Extracting menus to filter...")
    newMenus = trans.getSysMenuFile('')
    
    print("Filtering...")
    for proj in PROJ_NAMES_TO_REMOVE:
        print("\t-Removing: %s"%proj)
        newDlogs._projs.pop(proj, '')
        newStrTbl._projs.pop(proj, '')
        newMenus._projs.pop(proj, '')
    
    print("Creating new Translator...")
    newTrans.setSysFiles( ConvertMenuXML2CSV('', newMenus), newDlogs, newStrTbl)
    print("Saving...")
    newTrans.save(order=True)
    print("FINISHED!")
    
    



