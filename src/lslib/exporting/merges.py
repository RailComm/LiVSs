#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""This file has a bunch of utility functions that the Joiner object uses to 
in-place merge and manipulate merges of utility and translator files. These
wont be useful anywhere else but with the joiner so thats why its in this 
submodule. If in the even we want to break up the merging and the joining
processes more, then this should be moved, and several of the functions in
the utility files themselves will probably need to be re-factored. 
"""
import copy
import os.path as opath
import lslib.util.iohelp as iohelp

def ScanAndMergeMenus( newPath, menuFiles ):
    """Scans all files in a list and merges them together to make a project
    level file. This is considered a merge since its RCMenuFiles that are 
    being utilized. If there is a problem scanning, then the error is raised.
    """
    if len(menuFiles) < 1: return None
    from lslib.base.file.utility.MenuFile import ScanMenuFile, RCMenuFile
    
    # find headers for this particular resource
    headers = _getHeadersFromPath( menuFiles[0]._path )
    
    # scan all files with the headers, merging as we go.
    if len(menuFiles) == 1:
        mergedProjFile = copy.deepcopy(menuFiles[0])
        mergedProjFile._path = newPath
    else:
        mergedProjFile = RCMenuFile(newPath)
        for menufile in menuFiles: 
            ScanMenuFile(menufile, headers)
            mergedProjFile = RCMenuFile.merge(newPath, mergedProjFile, menufile, True, True)
    return mergedProjFile

def ScanAndMergeDialogs(newPath, dialogFiles): 
    """Scans all files in a list and merges them together to make a project
    level file. This is considered a merge since its RCDialogFiles that are 
    being utilized. If there is a problem scanning, then the error is raised.
    """
    if len(dialogFiles) < 1: return None
    from lslib.base.file.utility.DialogFile import ScanDialogFile, RCDialogFile
    
    # find headers for this particular resource
    headers = _getHeadersFromPath( dialogFiles[0]._path )
    
    # scan all files with the headers, merging as we go.
    if len(dialogFiles) == 1:
        mergedProjFile = copy.deepcopy(dialogFiles[0])
        mergedProjFile._path = newPath
    else:
        mergedProjFile = RCDialogFile(newPath)    
        for dialogfile in dialogFiles: 
            ScanDialogFile(dialogfile, headers)
            mergedProjFile = RCDialogFile.merge(newPath, mergedProjFile, dialogfile, True, True)
    return mergedProjFile

def ScanAndMergeStrings(newPath, stringFiles): 
    """Scans all files in a list and merges them together to make a project
    level file. This is considered a merge since its RCStrTblFiles that are 
    being utilized. If there is a problem scanning, then the error is raised.
    """
    if len(stringFiles) < 1: return None
    from lslib.base.file.utility.StrTblFile import ScanStringTableFile, RCStrTblFile
    
    # find headers for this particular resource
    headers = _getHeadersFromPath( stringFiles[0]._path )
    
    # scan all files with the headers, merging as we go.
    if len(stringFiles) == 1:
        mergedProjFile = copy.deepcopy(stringFiles[0])
        mergedProjFile._path = newPath
    else:
        mergedProjFile = RCStrTblFile(newPath)    
        for stringfile in stringFiles:
            ScanStringTableFile(stringfile, headers)
            mergedProjFile = RCStrTblFile.merge(newPath, mergedProjFile, stringfile, True, True)
    return mergedProjFile


def _getHeadersFromPath( path ):
    basePath = opath.dirname( path )
    headers = []
    for cpath, name in iohelp.dirwalk(basePath, filter=iohelp.RCFilters.HeaderFilter,
                                      ignore=iohelp.RCFilters.BinaryDirs):
        if name.lower().startswith("resource"):
            headers.append(cpath) 
    return headers
