#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""A MenuFile (*.menus) is a file that contains one or more menus that are used 
 within a given project. What is good about a menu file is that a single menu
 can contain all of its language/resource data so that it can be exported to
 multiple (or preferably ALL) of your resource files.
 
 Detailed Description:
             <RCMENUS save="">
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
             </RCMENUS>
             
Menus - This is the root node, it has one attribute 'save' which specifies the
        time that this document was last saved.
        
Menu -  A Menu is tree structure with three possible sub-nodes: 'Popup', 
        'MenuItem', and 'Separator'. It has one attribute 'id' which is the 
        IDR_* definition that the Resource uses to reference the menu object.
        
Popup - A Popup is technically a menu, but with different attributes and 
        another possible sub-node, 'title'. The title is the text that shows
        up in the Popup. The attributes are: 'idn' (which is used to uniquely
        describe the Popup in the system, just as id's are used to describe
        menuitems), and 'order' (which all nodes have except Menus and Menu 
        nodes, they describe the actual order they go in within the RC file).
        
Title - This describes all text that a menu contains. This means it can be 
        localized which means it will need to be switched out. So for every
        Popup or MenuItem there may be multiple Title[s] that each have a
        different 'langcode'. These langcodes tell the system which RC this
        text belongs in.
        
MenuItem - A Menu Item is a simple selectable item in a Popup or Menu. It has
        an 'id' (which is given by the rc file) and an 'order' (which is given
        by its logical placement within the tree).
        
Separator - A separator is just for reference and to keep everything logically
        together. Later this may be expanded upon but right now it just has an
        'order'.
"""
import os, time, logging
import xml.etree.ElementTree as ET
from lslib.base.file.msrcobj.menu import RCMenu, RCMenuNode, RCMenuNodeType 


def ScanMenuFile( menuFile, headerLst ):
    """Scan through the headers and make sure the file is correct."""
    from lslib.base.file.rchfile import findElemNumInGroup
    if headerLst is None or len(headerLst) < 1: 
        raise Exception("No headers to scan from!")
    def _scanNodeList( nodelist ):
        for node in nodelist:
            if node.reqIDScan():
                if node.type == RCMenuNodeType.MENUITEM:
                    searcher = findElemNumInGroup( node.value.getID().num , headerLst )
                    for lid,_ in searcher: node.value.addPossibleID( lid )
                else: #POPUP
                    _scanNodeList( node._children )
                    
    for menu in menuFile._menus:
        if menu.reqIDScan(): _scanNodeList( menu._nodes )
            
def InMemMenu( path, menus ):
    """An easy way to get a new file in one line. If you want to just save
    a group of menus."""
    f = RCMenuFile( path )
    f._menus = menus
    return f

class RCMenuFile:
    """ A Menu File is essentially an XML file that is used to house all of
    the menu information for any MSVS project in such a way as to be able
    to quickly pull out or push back language information (particularly the
    strings). 
    """
    def __init__(self, path):
        self._path = path
        self._menus = []
        
    @staticmethod        
    def merge( newpath, firstMenuFile, secondMenuFile, preloaded=True, bypassScan=False ):
        """Merge two RCMenuFiles, this is may be important during the step to
        get ALL RCMenuFiles into translation files. 
        """
        import copy
        totalMenus = RCMenuFile(newpath)
        if not preloaded:
            firstMenuFile.load() #load so we know we can reference ._menus
            secondMenuFile.load()
        ids = [ ] # to keep track of ones, we still need to remove.
        for node in firstMenuFile._menus:
            found = False
            for nodeb in secondMenuFile._menus:
                if node.id == nodeb.id:
                    totalMenus._menus.append(RCMenu.mergeMenu(node, nodeb, bypassScan))
                    found = True
                    break
            if not found:
                totalMenus._menus.append( copy.deepcopy(node) )
            ids.append( node.id )
        
        #Check to make sure we got all of the ids that were in secondMenuFile
        for nodeb in secondMenuFile._menus:
            if nodeb.id in ids: continue
            else: totalMenus._menus.append( copy.deepcopy(nodeb) )
            
        return totalMenus
        
    
    def update(self, otherMenuFile ):
        """Updates this file with the values present in the other, it will NOT 
        add new values, and will NOT change the order. It will only add new 
        langcodes and adjust already present ones.
        """
        for index in range(len(self._menus)):
            for omenu in otherMenuFile._menus:
                if self._menus[index].id == omenu.id:
                    self._menus[index].updateValues( omenu )
                    break
    
    def save(self, newpath=None):
        """Save the current RCMenuFile to its path."""
        if len(self._menus) == 0: return False
        if newpath is not None: self._path = newpath
        root = ET.Element("RCMENUS", attrib={"save":str(time.time())})
        for menu in self._menus:
            root.append(menu.asXMLNode())
        try:
            if self.__try_setup_path(self._path):
                tree = ET.ElementTree( root )
                try:    tree.write(open(self._path, "wb"))
                except: tree.write(open(self._path, "w"))
                return True
        except: pass
        return False
    
    def load(self, newpath=None):
        """Load the entire RCMenuFile into memory."""
        if newpath is not None: self._path = newpath            
        root = ET.parse(self._path).getroot()
        self._menus = [] #TODO: are we updating or should this really be deleted.
        menus = root.findall("MENU")
        for menu in menus:
            try:
                m = RCMenu(menu.attrib["id"])
                self.__fillNode(menu, None, m, 0)
                self._menus.append( m ) #TODO: merge new menu? might just be updating
                #By passing in None we make all found nodes add themselves to the menu.
            except Exception as e: logging.warning( e ); raise
        return True    
        
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