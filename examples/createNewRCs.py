#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
""" This script runs through a directory tree and copies the resource.h and 
*.rc file and creates new ones in that same directory with the same names, plus
`_#` is appended where # is the number of the lang-code you want. It will also
edit the *.vcxproj and *.vcxproj.filters file to keep everything importing 
fine in VS 2010.

This can be reused for any number of languages, then Headshot can be used to 
merge and push data into it. Using this script will guarantee that there are no
differences besides the strings themselves throughout the language files. 
Therefore it is recommended that you use this script to create any new 
resources. The reason being that context is not saved by Headshot, so keeping
the context the same is paramount.

NOTE: Make sure all *.vcxproj and *.vcxproj.filters files can be written to
    if EDIT_PROJ_FILES is True. Otherwise a permission error will get thrown.
    
NOTE: The DESTRUCTIVE variable allows the script to delete the previous 
    resource file that was there, allowing you to re-align older resource
    files. This means that if you have a language that was handwritten separate
    from the default language, you can align all elements again. This makes
    sure context is the same throughout. USE ONLY IF YOU'VE BACKED UP THE 
    STRINGS WITH HEADSHOT OR SET `MK_RES_BKUP` TO TRUE!
    
WARNING: Will NOT generate language files for directories missing a *.vcxproj
    file. This means that any project not updated to VS 2010, this script
    will ignore. 
    
WARNING: This will create language resource duplicates for every project,
    including those that may not even have strings that need to be localized.
    This should not matter, and in fact might help in the future when you want
    to add localizable strings. If this turns out to have negative effects,
    then please check 
"""

import sys
from os import remove 
import os.path as opath
from shutil import copy
import xml.etree.ElementTree as ET

from lslib.base.file.rcsfile import scanRCFile
from lslib.util.iohelp import dirwalk, RCFilters

## CHANGE THESE IF YOU NEED TO ##
NEW_LANG_CODE = '2058'  ## <---------------------CHANGE THIS!!!
#################################
DEFAULT_CODE  = '1033'  #DONT CHANGE UNLESS YOUR BASE LANG IS NOT ENGLISH
DESTRUCTIVE     = False # Remove old resources for NEW_LANG_CODE.
EDIT_PROJ_FILES = True  # Add the resource files to the filters and project file.
MK_PROJ_BKUP    = True  # Make backups of the filters and project file if its edited.
MK_RES_BKUP     = False # Make backups of the resource files, set to true if destructive.
#################################
RESTORE_BACKUPS = False # Change this to true to JUST restore the backups.
REMOVE_BACKUPS  = False # Removes the backups after running 
#################################


#### The following are the constants that can be used for editing your Project files. ###
BACKUP_TAG = "_BACKUP"
CUSTOM_BUILD_MESSAGE_NODE = {r"'$(Configuration)|$(Platform)'=='Debug Optimized|Win32'" : r"",
                             r"'$(Configuration)|$(Platform)'=='Debug|Win32'"           : r"",
                             r"'$(Configuration)|$(Platform)'=='Release|Win32'"         : r""}
							 
CUSTOM_BUILD_COMMAND_NODE = {r"'$(Configuration)|$(Platform)'=='Debug Optimized|Win32'" : r'', 
                             r"'$(Configuration)|$(Platform)'=='Debug|Win32'"           : r'',
                             r"'$(Configuration)|$(Platform)'=='Release|Win32'"         : r''}
							 
CUSTOM_BUILD_OUTPUTS_NODE = {r"'$(Configuration)|$(Platform)'=='Debug Optimized|Win32'" : r'',
                             r"'$(Configuration)|$(Platform)'=='Debug|Win32'"           : r'', 
                             r"'$(Configuration)|$(Platform)'=='Release|Win32'"         : r''} 
							 
FILTERS_CLINCLUDE_NODE = "Header Files"
FILTERS_CUSTOM_NODE = "Resource Files"
##########################################################################################

def getpath(oldpath, newname):
    """Joins the new name with the old path. The old path can have a file
    name, it just gets removed.
    """
    path = opath.split(oldpath)[0]
    return opath.join( path, newname )

def getname( path, ext='' ):
    name = opath.split(path)[1]
    return name[:name.index(".")]+ext

def getproj( path ):
    """Gets the project name, ie the base directory name."""
    dirs = opath.split(path)[0]
    return opath.basename(dirs)

def renameWithExt( oldfilename ):
    """Returns a name of the old file with a _# in it, where 
    # is the NEW_LANG_CODE as set above.
    """
    name, ext = opath.splitext(oldfilename)
    return "%s_%s%s"%(name, NEW_LANG_CODE, ext)

def mycopy( a, b , replace=False, mkbkup=False):
    if opath.exists(b):
        if mkbkup: copy(b,b+BACKUP_TAG)
        if replace: 
            print("!Removing Old: %s"%b)
            remove( b )
        else: 
            print("!Skipping because already exists: %s"%b)
            return
    print("Copying: %s \n\tTo: %s"%(a,b))
    copy(a,b)
    
def fixVCXproj( path, makebackups=True ):
    """Adds the build configurations to the project files."""
    if makebackups: 
        try: copy( path, path+BACKUP_TAG)
        except Exception as e: print("Couldn't make backup: %s"%e)
            
    root = ET.parse( path ).getroot()
    namespace = getNamespace(root.tag)
    # add our custom build node to the Item Group that has the other
    # resource files. There should also be a custom build for 2058 too
    itemgroups = root.findall("%sItemGroup"%namespace)
    includenode, buildnode, count = False, False, 0
    resname = getname(path, "_"+NEW_LANG_CODE+".rc")
    for itemgroup in itemgroups:
        count+=1
        try:
            if not includenode and headerNode(itemgroup,namespace):
                ET.SubElement(itemgroup,"%sClInclude"%namespace, attrib={"Include":"resource_%s.h"%NEW_LANG_CODE})
                includenode = True
            elif not buildnode and resourceNode( itemgroup,namespace ):
                sub = ET.SubElement(itemgroup,"%sCustomBuild"%namespace, attrib={"Include":resname})
                for condition, value in CUSTOM_BUILD_MESSAGE_NODE.items(): 
					if value == "": continue
                    msg = ET.SubElement(sub, "%sMessage"%namespace, attrib={"Condition":condition})
                    msg.text = value
                for condition, value in CUSTOM_BUILD_COMMAND_NODE.items(): 
					if value == "": continue
                    msg = ET.SubElement(sub, "%sCommand"%namespace, attrib={"Condition":condition})
                    msg.text = value
                for condition, value in CUSTOM_BUILD_OUTPUTS_NODE.items(): 
					if value == "": continue
                    msg = ET.SubElement(sub, "%sOutputs"%namespace, attrib={"Condition":condition})
                    msg.text = value
                buildnode = True
            if buildnode and includenode: break
        except Exception as e: print(e)
    
    if count > 0:
        if not buildnode: print("Could not find the build node in %s"%path)
        if not includenode: print("Could not find header item group in %s"% path)
        if not buildnode and not includenode: return
    else: 
        print("Are you sure this file is a project file: %s"%path)
        return
    # save our changes.
    print("Updating Project file: %s" % path )
    strip_namespace_inplace(root)
    root.attrib["xmlns"] = namespace[1:-1]
    tree = ET.ElementTree(root)
    tree.write( path , xml_declaration=True, encoding="utf-8" )
    
def headerNode( node, namespace ):
    """Determines whether the node is the item group responsible for
    holding all the resource header files. 
    """
    for elem in node.findall("%sClInclude"%namespace):
        if elem.attrib.get("Include",'').lower() == "resource.h":
            return True
    return False

def resourceNode( node, namespace ):
    """Returns whether this is the node that resource CustomBuild 
    nodes should be in.
    """
    return len(list(node.findall("%sResourceCompile"%namespace))) > 0
        
def getNamespace( tag ):
    """In visual studio project files, they use XML namespaces. Which need
    to be maintained. 
    """
    if tag[0] != '{': return ''
    else: return "{%s}"%tag[1:].partition('}')[0] 
                 
def fixProjFilters( path, makebackups=True):
    if makebackups: 
        try: copy( path, path+BACKUP_TAG )
        except Exception as e: print("Couldn't make backup: %s"%e)
            
    root = ET.parse( path ).getroot()
    
    namespace = getNamespace(root.tag)
    resname = getname(path, "_"+NEW_LANG_CODE+".rc")

    #The filters file is less important, we can just append our new nodes.
    # VS will take care of the rest.
    ET.SubElement(
        ET.SubElement(
            ET.SubElement(root, "%sItemGroup"%namespace), 
        "%sCustomBuild"%namespace, attrib={"Include":resname}),
    "%sFilter"%namespace).text = FILTERS_CUSTOM_NODE
    
    ET.SubElement(
        ET.SubElement(
            ET.SubElement(root, "%sItemGroup"%namespace), 
        "%sClInclude"%namespace, attrib={"Include":"resource_%s.h"%NEW_LANG_CODE}),
    "%sFilter"%namespace).text = FILTERS_CLINCLUDE_NODE

    # save our changes
    print("Updating Filters: %s" % path )
    strip_namespace_inplace(root)
    root.attrib["xmlns"] = namespace[1:-1]
    tree = ET.ElementTree(root)
    tree.write( path, xml_declaration=True, encoding="utf-8"  )
    
def strip_namespace_inplace(etree, namespace=None, remove_from_attr=True):
    """ Takes a parsed ET structure and does an in-place removal of all namespaces,
        or removes a specific namespacem (by its URL).
 
        Can make node searches simpler in structures with unpredictable namespaces
        and in content given to be non-mixed.
 
        By default does so for node names as well as attribute names.       
        (doesn't remove the namespace definitions, but apparently
         ElementTree serialization omits any that are unused)
 
        Note that for attributes that are unique only because of namespace,
        this may attributes to be overwritten. 
        For example: <e p:at="bar" at="quu">   would become: <e at="bar">
 
        I don't think I've seen any XML where this matters, though.
    """
    if namespace==None: # all namespaces                               
        for elem in etree.getiterator():
            tagname = elem.tag
            if tagname[0]=='{':
                elem.tag = tagname[ tagname.index('}',1)+1:]
 
            if remove_from_attr:
                to_delete=[]
                to_set={}
                for attr_name in elem.attrib:
                    if attr_name[0]=='{':
                        old_val = elem.attrib[attr_name]
                        to_delete.append(attr_name)
                        attr_name = attr_name[attr_name.index('}',1)+1:]
                        to_set[attr_name] = old_val
                for key in to_delete:
                    elem.attrib.pop(key)
                elem.attrib.update(to_set)
 
    else: # asked to remove specific namespace.
        ns = '{%s}' % namespace
        nsl = len(ns)
        for elem in etree.getiterator():
            if elem.tag.startswith(ns):
                elem.tag = elem.tag[nsl:]
 
            if remove_from_attr:
                to_delete=[]
                to_set={}
                for attr_name in elem.attrib:
                    if attr_name.startswith(ns):
                        old_val = elem.attrib[attr_name]
                        to_delete.append(attr_name)
                        attr_name = attr_name[nsl:]
                        to_set[attr_name] = old_val
                for key in to_delete:
                    elem.attrib.pop(key)
                elem.attrib.update(to_set)


def copyrcs( dir, removeOld=False, editProjFiles=True, mkProjBackups=True, mkResBackups=False ):
    """ Copies the default language resource files and renames them to have
    the new language code in them. Two pass, slower but it works.
    """
    def atPathExistsResource( path ): 
        return opath.exists(opath.join(opath.split(path)[0], "resource.h")) or \
               opath.exists(opath.join(opath.split(path)[0], "Resource.h"))
    projs = []
    
    # 1st Pass: Determine what resources to create and edit project files if need be
    filters = ['vcxproj','filters',   'vcproj']
    for cpath, name in dirwalk(dir, filter=filters, 
                                    ignore=RCFilters.BinaryDirs):
        proj = getproj( cpath )
        rc   = getpath(cpath, proj+".rc") 
        if opath.splitext(cpath)[1] == '.vcxproj':
            # make sure that the project even has resources
            # and the given resource doesn't already exist.
            if atPathExistsResource( cpath ) and \
               not opath.exists(renameWithExt(rc)):
                if editProjFiles: fixVCXproj( cpath, mkProjBackups )
                projs.append( proj )
            else: 
                print("!Skipping project file edit of: %s"%proj)
                if removeOld: projs.append(proj)
        elif editProjFiles and opath.splitext(cpath)[1] == '.filters':
            # make sure that the project even has resources
            # and the given language resource doesn't already exist
            if atPathExistsResource( cpath ) and \
               not opath.exists(renameWithExt(rc)):
                fixProjFilters( cpath, mkProjBackups ) 
        ## Purely for warnings!
        elif opath.splitext(cpath)[1] == ".vcproj":
            print("!---> Project '%s' has not been updated to VS 2010! SKIPPING!"%proj)
                
    # 2nd Pass: We add all of our resources!
    filters = RCFilters.HeaderFilter + RCFilters.RCFilter
    for cpath, name in dirwalk(dir, filter=filters, 
                                    ignore=RCFilters.BinaryDirs):
        proj = getproj(cpath)
        if proj not in projs: continue # project was not updated, or doesn't need to be.
        
        if name.lower() == "resource.h":
            newpath = getpath(cpath, renameWithExt( "resource.h" )) #make sure all created headers are lowercase
            mycopy(cpath, newpath, removeOld, mkResBackups)
        elif opath.splitext(cpath)[1] == ".rc":
            if scanRCFile(cpath, defaultLang=DEFAULT_CODE)._langcode == DEFAULT_CODE:
                newpath = getpath(cpath, renameWithExt( name ))
                mycopy(cpath, newpath, removeOld, mkResBackups)
            else: continue
        
def restoreBackups( dir ):
    bklen = len(BACKUP_TAG)
    for cpath, name in dirwalk(dir, ignore=RCFilters.BinaryDirs):
        if name[-bklen:] == BACKUP_TAG:
            newpath = cpath[:-bklen]
            # delete the old one
            remove(newpath)
            # restore old old backup
            copy( cpath, newpath )
            # remove backup file
            remove(cpath)
            print("Restored backup of: %s"%newpath)
            
def removeBackups( dir ):
    bklen = len(BACKUP_TAG)
    for cpath, name in dirwalk(dir, ignore=RCFilters.BinaryDirs):
        if name[-bklen:] == BACKUP_TAG:       
            remove(cpath)
            print("Removed backup: %s"%cpath)


if __name__ == "__main__":
    print("%d,%s"%(len(sys.argv),sys.argv))
    if len(sys.argv) != 2:
        print("ERROR: Invalid argument(s), must give a directory path.") ; exit(1)
    elif not opath.exists(sys.argv[1]):
        print("ERROR: Path does not exist!") ; exit(1)
    elif not opath.isdir(sys.argv[1]):
        print("ERROR: Argument is not a directory!") ; exit(1)
    elif RESTORE_BACKUPS:
        restoreBackups(sys.argv[1])
    else: 
        copyrcs( sys.argv[1],
                   removeOld=DESTRUCTIVE,
                   editProjFiles=EDIT_PROJ_FILES,
                   mkProjBackups=MK_PROJ_BKUP,
                   mkResBackups=MK_RES_BKUP )
        if REMOVE_BACKUPS: removeBackups( sys.argv[1] )
    
    