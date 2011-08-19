#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#

import os

# Here are some special filter and exclusion lists.
class RCFilters:
    RCFilter = ['rc','rcs']
    HeaderFilter = ['h']
    UtilityFilter = ['menus','dialogs','strtbls']
    SysLevelFilter= ['master.menus','master.dialogs','master.strtbls']
    MenuFilter = ['menus']
    StrTblFilter = ['strtbls']
    DialogFilter = ['dialogs']
    BinaryDirs = ['Debug','Debug Optimized','Release','res']


def setup_path( path, mode='r+' ):
    """Create a file and the whole path to it. Returns the
    file object in the mode given or None if couldn't create
    or open."""
    if os.path.exists(path):
        if os.access(path, os.W_OK):
            return open( path, mode )
        else: return None
    else:
        try:
            dirs, _ = os.path.split(path)
            if not os.path.exists(dirs):
                os.makedirs(os.path.abspath(dirs))
        except: return None
        return open( path, mode )
        
def _formatExt( ext, ignoremulti=False ): 
    """Formats an extension given to be checkable, LiVSs compaires
    extensions without the 'dot'.
        Types of formatting accounted for:
            '*.txt'   -Wildcards
            '.txt'    -no names
            'hi.txt'  -examples
            'txt'     -just extension
          (For all of the above the return will be 'txt'.)
            ''        -blanks
            None      -null
          (For above will return None.)
            '*'       -complete wildcard
            '*.*'     -complete matching
          (For above will return blank string, ''.)
        For all forms of multiextensions the whole extension is returned:
            ie. '*.tar.gz' - returns 'tar.gz'
            so avoid periods in the name, ie
                'temp.htaccess.txt' -will return 'htaccess.txt'
            however to avoid getting the first part removed, make sure
            there is a wildcard in front.
                '*.tar.gz' = 'tar.gz'
                '.tar.gz'  = 'tar.gz'
                'tar.gz'   = 'gz'
    """
    try:
        if type(ext) is not str: f = str(ext)
        else: f = ext
        
        f = f.trim()
        if f is None or f is '': return None
        elif f is '*' or f is '*.*': return ''
        else:
            a,*b = f.split(".")
            c = len(b)
            if c is 0: return a
            elif c is 1: return b[0]
            else: 
                if ignoremulti: return b[-1]
                else: return ".".join(b)
    except: return None       

def determine_extension( path, ignoremulti=False ):
    """Returns the extension of the path, None if path is a directory. 
    If a file without extension (ie 'README'), will return empty string.
    Extension returned will be without the 'dot', (ie 'Readme.txt' will
    return 'txt').
    """
    try:
        if os.path.isdir( path ): return None
        elif os.path.isfile( path ):
            return _formatExt( path, ignoremulti )
        else: return None
    except: return None
    
def fileok( filename, exclude=None, filter=None ):
    """Given an exclusion list and a filter list, this function
    determines if a file is ok by looking at its extension. For
    definitions of how exclusions and filters work, check the 
    HOWTO.
    """
    fltr,excl = [],[]
    if exclude is not None: excl = exclude
    if filter is not None: fltr = filter
    ext = os.path.splitext(filename)[1][1:]
    if ext in excl: return False
    if len(fltr)==0 or \
       ext in fltr: return True
    return False
    
def ignoredirectory( dir, ignoredirs=None ):
    """Checks whether to ignore the directory by
    checking out its name."""
    try:
        dirname = str(dir).split("\\")[-1]
        if ignoredirs is None or \
           dirname in ignoredirs: return True
        else: return False
    except: return False
     
def dirwalk( directory, exclude=None, filter=None, ignore=None ):
    """Walks through a directory and excludes certain file types
    or filter to just get certain file extensions. This function
    returns an iterator that can be used in place of os.walk.
    the return from dirwalk is not a three-tuple but instead just
    a tuple (cpath, name) where:
        cpath = the complete path of the file (can be passed to open)
        name  = the trimmed name of the file (can be used for printing)
    """
    for root, _, files in os.walk( directory ):
        if ignoredirectory( root, ignore ): continue
        for file in files:
            if fileok( file, exclude, filter ):
                yield (os.path.join(root, file), file)
    
def filename( path ):
    """ Return the name of the file, given a path."""
    _, name = os.path.split( path )
    if name == '': return None
    else: return os.path.splitext( name )
    
def lastdirname( path ):
    """Returns the last directory in the path. (eg, 
    ~/docs/work/2011/code/file.cpp will return 'code')
    """
    dirs, _ = os.path.split( path )
    return os.path.basename(dirs)
    
def dirwalkl( directory, exclude=None, filter=None, ignore=None ):    
    """Works exactly like dirwalk, except that it yields a list
    of matches per directory, rather than every single match.
    """
    curdir = ''
    ret = []
    import logging
    for cpath, name in dirwalk(directory, exclude, filter, ignore):
        if filter==RCFilters.HeaderFilter: logging.debug("FOUND HEADER MATCH: %s"%name)
        if os.path.dirname(cpath) == curdir: #add to return list
            ret.append((cpath,name))
        else: #return the list if we have one, otherwise mark as new
            if len(ret) > 0: 
                yield ret
                ret = []
            curdir = os.path.dirname(cpath)
            ret.append((cpath,name))
    
def ScanUntilMatch( path, check ):
    """ Scans a file until a line matches the check. If no line
    matches, it returns None.
    """
    import fileinput
    reader = fileinput.FileInput([path], mode='r')
    for line in reader:
        if check.search(line) is not None: return line, reader
    return None

def ScanUntilNotMatch( path, check ):
    """Scans a file until there isn't something that matches the 
    regex that was passed in. If the whole file matches, then it
    returns None. 
    """
    import fileinput
    reader = fileinput.FileInput([path], mode='r')
    for line in reader:
        if check.search(line) is None: return line, reader
    return None