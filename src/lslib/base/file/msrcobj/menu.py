#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""Menus are hierarchical structures that form drop-down menus of an 
application. These have strings that must be localized and an order
that must be maintained. This causes some problems for how to hold
this data. XML is perfect, and so MenuFiles.py pushes and pulls
resource files into XML.

Here is an example menu from a resource file:

IDR_MAINFRAME MENU
BEGIN
    POPUP "&Window"
    BEGIN
        POPUP "&Zoom"
        BEGIN
            MENUITEM "Zoom &Out",               ID_WINDOW_ZOOM_ZOOMOUT
            MENUITEM "Zoom &In",                ID_WINDOW_ZOOM_ZOOMIN
            MENUITEM "Zoom O&riginal",          ID_WINDOW_ZOOM_ZOOMORIGINAL
        END
        MENUITEM "&Full Screen",                ID_WINDOW_FULLSCREEN
        MENUITEM SEPARATOR
        MENUITEM "&New Window",                 ID_WINDOW_NEW
        MENUITEM "&Cascade",                    ID_WINDOW_CASCADE
        MENUITEM "Tile &Horizontal",            ID_WINDOW_TILE_HORZ
        MENUITEM "Tile &Vertical",              ID_WINDOW_TILE_VERT
        MENUITEM "&Arrange Icons",              ID_WINDOW_ARRANGE
        MENUITEM "S&plit",                      ID_WINDOW_SPLIT
    END
    POPUP "&Help"
    BEGIN
        MENUITEM "&About My Program...", ID_APP_ABOUT
    END
END

To see how this is parsed into this object. Check out MenuFile.py or 
rcsfile.py in lslib.base.file.utility.
"""

import xml.etree.ElementTree as ET
from lslib.base.file.msrcobj.msobjbase import * #@UnusedWildImport


class RCMenu:
    """The RCMenu is the object stored in memory that represents a single
    menu within one or more resource files. (eg, One or more languages.) 
    The reason it has no 'loading' functions is because it discourages 
    runtime loading in places other than file interactions. So go look at
    MenuFile.py.
    """
    def __init__(self, id):
        self.id = id
        self._nodes = []
         
    def addChild(self, node):
        """ Utility function to make RCMenu seem like a RCMenuNode. """
        self._nodes.append( node )
        
    def getChild(self, id):
        """Get the Child node based on its ID. It will even look though all 
        of the children it has for it.
        """
        val = None
        for child in self._nodes:
            if child.getIdentifier() == id:
                val = child
                break
        if val is None: 
            for child in self._nodes:
                try: 
                    val = child.getChild(id)
                    if val is not None: break
                except: continue
        return val 
        
    def getIdentifier(self):
        return "%s"%str(self.id)
    
    def findParentOfNode(self, xpath ):
        """ Find the parent of a node based on the XPath of identifiers. """
        if len(xpath.split('.')) == 1: return self
        def _recurseIntoNode( xpathlst, node ):
            if len(xpathlst)==0: return node
            else:
                for child in node._children:
                    if child.getIdentifier() == xpathlst[0]:
                        return _recurseIntoNode(xpathlst[1:], child)
                return None #shouldn't have gotten here.
        
        pathparts = xpath.split('.')[:-1] #ignore the last part since its the actual id
        if len(pathparts)==0: return self
        
        for node in self._nodes:
            if pathparts[0] == node.getIdentifier():
                return _recurseIntoNode(pathparts[1:], node)
                

    def combine(self, other):     
        """Combines another menu with this one. Its similar to merge, except
        its in place, and does not return anything unless there is an exception
        thrown from one of the functions.
        """
        for anode in other._nodes:
            found = False
            for bnode in self._nodes:
                if bnode.type == RCMenuNodeType.SEPARATOR:
                    found = True
                    break
                elif bnode.isSame(anode): 
                    bnode.combine(anode)
                    found = True
                    break
            if not found: self._nodes.append( anode )
         
    @staticmethod
    def mergeMenu(firstMenu, otherMenu, bypassScan=False):
        """Merges the two menus. If they are the same menu then it will
        return a new menu with both both langcodes. The analysis of the
        two menus requires them to be the same, so if they arn't an
        Exception will be raised. An Exception will also be raised if 
        there was a problem with the merging process.
        """
        if type(firstMenu) is not RCMenu or \
           type(otherMenu) is not RCMenu:
            raise TypeError("Merging dialogs needs two dialogs.")
        
        if firstMenu.id != otherMenu.id:
            raise AttributeError("Merging dialogs needs two dialogs of the same ID.")
        
        if not bypassScan and (firstMenu.reqIDScan() or otherMenu.reqIDScan()):
            ## An ID scan makes sure all 
            raise AttributeError("Cannot merge until one or both menus get an ID scan.")
        
        if firstMenu.size() < otherMenu.size():
            ## We want the largest menu to be the base menu.
            return RCMenu.mergeMenu(otherMenu, firstMenu)
        
        import copy
        newMenu = RCMenu(firstMenu.id)
        newlst = []
        for node in firstMenu._nodes: newMenu._nodes.append( copy.deepcopy(node) )
        for anode in otherMenu._nodes:
            if anode.type == RCMenuNodeType.SEPARATOR: continue
            found = False
            for index in range(len(newMenu._nodes)):
                if newMenu._nodes[index].isSame(anode, bypassScan): 
                    newMenu._nodes[index].combine( anode, bypassScan )
                    found = True
                    break
            if not found:
                logging.warning("Node could not be matched, tagged as possible error.\n\t%s: %s"%
                                    (anode.getXPath(),
                                     ET.tostring(anode.asXMLNode())))
                newlst.append( RCMenuNode.tagError(anode) )
        newMenu._nodes.extend(newlst)
        return newMenu
    
    def updateValues(self, otherMenu):
        """Update all values with the values in the other menu. This means 
        that NO NEW VALUES ARE ADDED, it just overwrites the values in the
        current menu with the values in the other. It also allows for adding 
        new language codes for each particular value.
        """
        for index in range(len(self._nodes)):
            for onode in otherMenu._nodes:
                if self._nodes[index].getIdentifier() == onode.getIdentifier():
                    self._nodes[index].update( onode )
                    break
    
    
    def reqIDScan(self):
        """Checks whether there are values in the menu that do not have an ID 
        associated with them.
        """
        for node in self._nodes:
            if node.reqIDScan(): return True
        return False
    
    def size(self):
        """Finds the number of 'elements' in the whole menu."""
        def _size( curmax, node ):
            if node.type != RCMenuNodeType.POPUP:
                return node.orderid if node.orderid > curmax else curmax
            else: 
                for child in node._children: 
                    curmax = _size( curmax, child )
                return curmax
                
        curmax = 0
        for node in self._nodes: 
            curmax = _size( curmax, node )
        return curmax     
    
    def asRCString(self, langcode='1033', aslist=False, defaultLangcode='1033'):
        """Generates the structure of the RCMenu in the RC file format."""
        ret = "%s MENU\nBEGIN\n"%self.id
        for node in self._nodes: ret+=node.asString(langcode, defaultLangcode=defaultLangcode)
        ret+="END\n"
        
        if aslist:
            return ret.splitlines(True)
        else:
            return ret
        
    def asXMLNode(self):
        """Generates an XML structure out of our RCMenu."""
        node = ET.Element("MENU", attrib={"id":self.id})
        for child in self._nodes:
            tmp = child.asXMLNode()
            if tmp is not None: node.append( tmp )
        return node
            
    def getValueSpacing(self, langcode):
        """Used for generating the RC String so that all IDs are aligned."""
        val = 1
        for node in self._nodes:
            val = max(val, node.maxSize(langcode))
        return val+1#adjustment made by msvs 
    
    def getNewIDN(self):
        """In order to keep things lined up we need to be able to reference idn's between 
        instances of RCMenus. This is so we can check between different language codes.
        (ie, if we have two RCMenus for the same menu but one in spanish and another in 
        english. All of the concurrent nodes will need to match.)
        """
        import uuid #standard win uuid creation.
        return uuid.uuid4()


###############################################################################
##############################  MENU NODES  ###################################
###############################################################################

class RCMenuNodeType:
    """The type that a RCMenuNode can be, there are only three
    choices POPUP, a normal MENUITEM, and a SEPARATOR.
    """
    SEPARATOR, MENUITEM, POPUP = range(3)
    HAS_STRING = [1,2]
    
    @staticmethod
    def getType(s):
        """Convert the string version of a type into its
        Enumerated value.
        """
        if s == "SEPARATOR": return RCMenuNodeType.SEPARATOR
        elif s == "MENUITEM": return RCMenuNodeType.MENUITEM
        elif s == "POPUP": return RCMenuNodeType.POPUP
        else: raise TypeError("Invalid Menu Node Type: %s"%s)
    @staticmethod
    def strType(t):
        """Return a string version of the Type."""
        return ["SEPARATOR","MENUITEM","POPUP"][t]



class RCMenuNode:
    """A node is a single element on a Menu section within an rc file.
    The parsing for this object is done in RCSFile, but the storage
    for any single node is within a RCMenu object.
    """
    INDENT=" "*4#four spaces per MSVS spec.
    def __init__(self, menuref, id=None, 
                                type=RCMenuNodeType.MENUITEM, 
                                idn=None, order=None):
        
        self.__menuref = menuref
        self._parent   = None
        self._children = []
        self.orderid   = 0 if order is None else order
        self.idn       = idn
        self.value     = RCStringValue( id )
        self.type      = type
        self.error     = False
        
        self.__validateIDN()
    
    @staticmethod
    def tagError( node ):
        """Returns a copy of the given node that has been tagged as an error."""
        import copy
        newnode = copy.deepcopy(node)
        newnode.error = True
        return newnode
    
    def reqIDScan(self):
        """Checks if this or any child nodes needs assistance in associating
        itself with an ID. (i.e., needs to look at the master header file.)
        """
        if self.type == RCMenuNodeType.SEPARATOR: return False
        elif self.type == RCMenuNodeType.MENUITEM:
            return self.value.reqIDScan()
        else:
            for child in self._children:
                if child.reqIDScan(): return True
            return False
    
    def numSub(self):
        """Finds the number of times this node is a child. Used to find
        how many times to indent it as a block.
        """
        if self._parent is None: return 1
        else: return self._parent.numSub() + 1
        
    def maxSize(self, langcode):
        """Finds the size of the largest 'value' in the node tree. This is
        so that we can space the IDs out far enough away just like MSVS does.
        """
        if self.value is None: val = 0
        else: val = len(self.value.getValue(langcode, ''))
        for child in self._children: 
            val = max(val, child.maxSize(langcode))
        return val
    
    def addChild(self, node):
        """Add a child to this Menu Node."""
        if not isinstance(node, RCMenuNode):
            return TypeError("To add a child it must be of type RCMenuNode.")
        if self.type != RCMenuNodeType.POPUP:
            return TypeError("This type of node can not have subnodes.")
        self._children.append( node )
        node._parent = self
    
    def getChild(self, id):
        """Get the Child node based on its ID. It will even look though all 
        of the children it has for it.
        """
        if self.getIdentifier() == id:
            return self
        
        val = None
        for child in self._children:
            if child.getIdentifier() == id:
                val = child
                break
        if val is None: 
            for child in self._children:
                try: 
                    val = child.getChild(id)
                    if val is not None: break
                except: continue
        return val
    
    def getLangCodes(self):
        """Returns a list of the language codes that are used in this node."""
        lst = {}
        for e in self.value.getLangCodes():
            lst[e] = 1
        return lst.keys()
        
    def getIdentifier(self):
        """Returns menuitem's IDs but the IDNs of everything else. Since popups
        and separators both don't have anything we can reference them by we 
        generated them some identification.
        """
        if self.value is None or self.value.getID() is None:
            return self.idn
        else: return self.value.getID()
        
    def isSame(self, other, checkPossibles=False, shallow=False):
        """Checks to see if this and the other node represent the same node in
        a menu.
        """
        def __compareIDPossibilities( aval, bval ):
            return aval.getID() in bval.getPossibleIDs() or \
                   bval.getID() in aval.getPossibleIDs()
        
        if other.type != self.type: return False
        elif other.type == RCMenuNodeType.SEPARATOR:
            ## If they are a separator we have to ignore them. There
            ## is no way to accurately merge separators and maintain their
            ## order in relation to everything else. 
            return None
        elif other.type == RCMenuNodeType.MENUITEM:
            ## MenuItems are easy as they have unique IDs.
            if self.value.getID() == other.value.getID():
                return True
            elif checkPossibles: 
                return __compareIDPossibilities( self.value, other.value )
            else: return False
        else: # other.type == POPUP
            ## Compare IDN, however this is generated by us and isn't
            ## conclusive if its not the same. So we must rely on order,
            ## or its sub-elements to classify it.
            if other.idn == self.idn: return True
            elif not shallow:
                ## We need to look at the sub-elements. 
                ## It is possible for another popup in the same menu to
                ## have the same id (two places do the same thing). So we
                ## need to only say no if the majority is a no. (yes, hackish)
                count=0
                for sub in self._children:
                    for subb in other._children:
                        if sub.isSame( subb, checkPossibles, shallow=True ): 
                            count+=1
                return count > max(len(self._children), len(other._children))/2
            else: 
                return self.orderid == other.orderid
    
    def combine(self, other, checkPossibles=False):
        """Combines two nodes. Make sure you run isSame on it beforehand,
        as well as check that they are in the same menu, as some things are
        assumed because of these two pre-conditions.
        """
        import copy
        if self.type not in RCMenuNodeType.HAS_STRING: return
        self.value.combine( copy.deepcopy( other.value ) ) #both menuitems and popups
        if self.type == RCMenuNodeType.POPUP:
            newlst = []
            for anode in other._children:
                if anode.type == RCMenuNodeType.SEPARATOR: continue
                found = False
                for index in range(len(self._children)):
                    if self._children[index].isSame(anode, checkPossibles): 
                        self._children[index].combine( copy.deepcopy(anode) )
                        found = True
                        break
                if not found:
                    logging.warning("Node could not be matched, tagged as possible error.\n\t%s: %s"%
                                    (anode.getXPath(),
                                     ET.tostring(anode.asXMLNode())))
                    newlst.append( RCMenuNode.tagError(anode) )
            self._children.extend( newlst )
     
    def asString(self, langcode='1033', showOrder=False, defaultLangcode='1033'):
        """Returns the Node as a String in the format of an RCFile. This makes
        It simple to output back into an RCFile if you want to dump it all back
        in. However if you want to surgically edit the RCFile (which is 
        recommended), use the rcsfile.py.
        """
        ret = "" if not showOrder else "%d"%self.orderid
        indent = self.__getIndent()
        if self.type == RCMenuNodeType.SEPARATOR: 
            ret += "%sMENUITEM SEPARATOR\n"%indent
            return ret
        
        val = self.value.getValue(langcode, self.value.getValue(defaultLangcode, None))
        if val is None: return ret # we ignore if we don't have the langcode
        elif val == '' and self.value.getValue(defaultLangcode, '') != '':
            val = self.value.getValue(defaultLangcode, '')
        if self.type == RCMenuNodeType.MENUITEM:
            ret += "%sMENUITEM \"%s\",%s %s\n"%(indent,val,
                                            self.__getSpacing(langcode),
                                            self.value.getID())
        elif self.type == RCMenuNodeType.POPUP:
            ret += "%sPOPUP \"%s\"\n%sBEGIN\n"%(indent,val,indent)
            for child in self._children: 
                try:ret+=child.asString(langcode, showOrder)
                except Exception as e: logging.exception(e)
            ret+= "%sEND\n"%indent
        return ret
    
    def getXPath(self):
        def _getParentXPath():
            if self._parent is None: return self.__menuref.id
            else: return self._parent.getXPath()
        return "%s.%s"%(_getParentXPath(), self.getIdentifier())
    
    def asXMLNode(self):
        """Returns the Node as an XML node (xml.etree.Element). This is compiled 
        and added together in the RCMenu object and then written/parsed by the
        RCMenuFile object.
        """
        node = None
        if self.type == RCMenuNodeType.SEPARATOR:
            att = {"order":str(self.orderid),"idn":str(self.idn)}
            if self.error: att['error'] = 'True'
            node = ET.Element("SEPARATOR", attrib=att)
        elif self.type == RCMenuNodeType.MENUITEM:
            att = {"id":str(self.value.getID()),"order":str(self.orderid)}
            if self.error: att['error'] = 'True'
            node = ET.Element("MENUITEM",attrib=att)
            for langcode in self.value.getLangCodes():
                sub = ET.SubElement(node, "TITLE", attrib={"langcode":langcode})
                sub.text = self.value.getValue(langcode, "")
        elif self.type == RCMenuNodeType.POPUP:
            att = {"idn":str(self.idn),"order":str(self.orderid)}
            if self.error: att['error'] = 'True'
            node = ET.Element("POPUP", attrib=att)
            for langcode in self.value.getLangCodes():
                sub = ET.SubElement(node, "TITLE", attrib={"langcode":langcode})
                sub.text = self.value.getValue(langcode, "")
            for child in self._children:
                tmp = child.asXMLNode()
                if tmp is None: continue
                else: node.append(tmp)
        return node
    
    
    def update(self, otherNode):
        """Updates the current node with the values of the other one. Useful
        for push-back time.
        """
        if self.type == RCMenuNodeType.SEPARATOR: return
        self.value.combine( otherNode.value, intelligent=False )
        if self.type == RCMenuNodeType.POPUP:
            for cindex in range(len(self._children)):
                for ochild in otherNode._children:
                    if self._children[cindex].getIdentifier() == ochild.getIdentifier():
                        self._children[cindex].update( ochild )
                        break
    
    
    def __getIndent(self):
        return self.INDENT*self.numSub()
        
    def __getSpacing(self, langcode):
        if self.value is None: return ""
        tmp = self.__menuref.getValueSpacing(langcode)-len(self.value.getValue(langcode, ''))
        return " "*tmp

    def __validateIDN(self):
        if self.type != RCMenuNodeType.MENUITEM:
            if self.idn is None:
                self.idn = self.__menuref.getNewIDN()
        