#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""On base utility menu files, the root node is RCMENUS, and it holds
the time of creation and some other stuff if need be. However in System
level files, the root node is SYSTEM and inside it are a list of PROJECT
nodes, which are essentially the RCMENUS from before but renamed.
   Here is detailed layout of the XML:
                <SYSTEM save="">
                    <PROJECT name="">
                        <MENU id="IDR_MAINFRAME">
                            <POPUP idn="823489hjh9d1n90" order="1">
                                 <TITLE langcode="1033">&amp;User</TITLE>
                                 <TITLE langcode="2058">&amp;Usario</TITLE>
                                 <MENUITEM id="ID_USER_LOGIN" order="2">
                                     <TITLE langcode="1033">&amp;Login</TITLE>
                                     <TITLE langcode="2058">Ingresar</TITLE>
                                 </MENUITEM>
                             </POPUP>
                             ...
                             <SEPARATOR idn="" order="50" />
                             ...
                         </MENU>
                         ...
                    </PROJECT>
                    ...
                </SYSTEM>
                
All parsing of this file type happens in the SysMenuFile object, and shouldn't
be moved as there is no need to delve much deeper than what functions are 
provided via the BaseUtilityFileWrapper object. Any accessors can be pushed to
a per-project level.
"""
import os
import time
import copy
import logging
import xml.etree.ElementTree as ET

from lslib.base.file.utility.MenuFile import RCMenuFile,InMemMenu
from lslib.base.file.msrcobj.menu import RCMenu, RCMenuNode, RCMenuNodeType
from lslib.base.file.syslvl.sysbase import BaseUtilityFileWrapper, \
                                           isSystemLevelMenu


class SysMenuFile( BaseUtilityFileWrapper ):
    """This is the object that allows you to pull individual projects' menu 
    files in and out of the master System Menu Files. To utilize it, just
    give it a path name of the system file and call load.
    """
    def __init__(self, path):
        if not isSystemLevelMenu( path ):
            raise TypeError("Path given is not a system level menu file.")
        self._path = path
        self._projs = {} #map: "projname"-> [list of RCMenus]
        self.__loaded = False
        
    def load(self, newpath=None): 
        if newpath is not None:
            if not isSystemLevelMenu( newpath ):
                raise TypeError("Path given is not a system level menu file.")
            else: self._path = newpath
        root = ET.parse(self._path).getroot()
        self._projs = {}
        projects = root.findall("PROJECT")
        for project in projects:
            try:
                menus = project.findall("MENU")
                lst = []
                for menu in menus:
                    m = RCMenu( menu.attrib["id"])
                    self.__fillNode( menu, None, m, 0 )
                    lst.append( m )
                self._projs[ project.attrib["name"] ] = lst
            except Exception as e: logging.warning( e )
        self.__loaded = True
        return True
        
    def save(self, newpath=None, timestamp=True):
        # we don't care about checking if its syslvl, we are overwriting.
        if newpath is not None: self._path = newpath
        sysattrib={}
        if timestamp: sysattrib["save"] = str(time.time()) 
        root = ET.Element("SYSTEM", attrib=sysattrib)
        for name, menus in self._projs.items():
            proj = ET.SubElement(root, "PROJECT", attrib={"name":name})
            for menu in menus:
                proj.append( menu.asXMLNode() )
        try:
            if self.__try_setup_path( self._path ):
                tree = ET.ElementTree( root )
                try:    tree.write( open(self._path, "wb") )
                except: tree.write( open(self._path, "w")  )
                return True
        except Exception as e: 
            logging.error("Could not save System Menu File: %s"%e)
        return False
        
    def getProjectList(self):
        return list(self._projs.keys())
    
    def removeProjLevelFile(self, projName): 
        return self._projs.pop(projName, None) is not None
    
    def addProjLevelFile(self, projName, path, obj=None, overwrite=True): 
        if not overwrite and projName in self._projs:
            raise KeyError("Project already exists!")
        if obj is None:
            file = RCMenuFile( path )
            if not file.load():
                raise Exception("Could not load Menu File!")
        else: file = obj
        self._projs[ projName ] = copy.deepcopy(file._menus)
        return True
    
    def genProjLevelFile(self, projName, newPath, autosave=False):
        if projName not in self._projs:
            raise KeyError("Project wasn't found in the system file.")
        file = InMemMenu( newPath, self._projs[projName] )
        if autosave: file.save()
        return file
    
    def updateFromTranslation(self, otherSysFile, autosave=False):
        for proj in self._projs.keys():
            omenus = otherSysFile._projs[proj]
            for index in range(len(self._projs[proj])):
                # for each menu in self, find it in the other file
                # and update it with the values in that one.    
                for omenu in omenus:
                    if self._projs[proj][index].id == omenu.id:
                        self._projs[proj][index].updateValues( omenu )
                        break
        if autosave: self.save()
    
    
    def __fillNode(self, elems, node, menu, order):
        """Recursive function for filling the nodes in the RCMenus when reading from
        the MenuFile.
        """
        for elem in elems:
            try:
                # When dropping down into POPUPs we will see titles, lets ignore them.
                if elem.tag == "TITLE": continue
                
                subnode = RCMenuNode(menu,id=elem.attrib.get("id", None),
                                            type=RCMenuNodeType().getType(elem.tag),
                                            idn=elem.attrib.get("idn", None),
                                            order=elem.attrib.get("order", order))
                order+=1 ##increment order.
                
                ## Both POPUPs and normal MENU_ITEMS have titles that need to be grabbed.
                if subnode.type!=RCMenuNodeType.SEPARATOR:
                    titles = elem.findall("TITLE")
                    for title in titles:
                        try: subnode.value.addValuePair(title.attrib["langcode"], title.text)
                        except: pass
                        
                ## POPUPs need to be recursively called to grab all internal elements too.
                if subnode.type==RCMenuNodeType.POPUP:
                    try: self.__fillNode(elem, subnode, menu, order)
                    except: raise
                
                ## If this was a top-level node add it to the menu. Otherwise add it to the node
                ## that was passed in.
                if node is None: menu._nodes.append( subnode )
                else: node.addChild( subnode )
            except: raise
    
    def __try_setup_path(self,path):
        if os.path.exists(path):
            return os.access(path, os.W_OK)
        else:
            try:
                dirs, _ = os.path.split(path)
                if not os.path.exists(dirs):
                    os.makedirs(os.path.abspath(dirs))
            except:
                return False
            return True      