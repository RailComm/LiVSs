#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""In order to get all menu information in and out of a translation file we
need to be able to decompose a hierarchy into a flat table. We can do that
with our special LSCSV files.

There are three sections to a sys-lvl menu csv file: 'Data', 'Projects',
and 'Util'. Here are discriptions of each:

[Data]
The data section is very similar to the other CSVs used in the LiVSs 
system. It has id's mapped to their language values in the form. 
           id, langcode [, langcode [, langcode [, ...]]]
           
The id for each row, in this instance, is of the form:
                    <projID>.<nodesXPath>
                       
The node's XPath is a standard XML XPath that is generated in MenuFile. This
is a quick way of recording the structure. The project ID is held in the 
following section.

[Projects]
This section holds a mapping of numbers to project name. This is so we can 
keep track and merge this listing later on. For completeness sake here is the
form that the rows take:
                    <number>,<projectname>

[Util]
This is probably the most complicated and un-intuitive portion of the file.
It has three columns and keeps track of all of the other information that is
needed by the reconstruction process:
                    <idn>,<order>,<type>
                    
<idn> - this is the exact id of the node with the project's number on the 
        front, (not an xpath). For Popups and seperators this is their IDN 
        number, for MenuItems this is their resource ID string.
                    <projID>.<id>
<order> - this is the number given to it as its hierarchical order.
<type>  - this is a choice between "SEPARATOR", "MENUITEM", or "POPUP".

More information is provided in the class below, but there is also more info
in TranslationFile.py located with the rest of the utility files.
"""
import copy
import logging

from lslib.base.file.lscsv import LSCSV
from lslib.base.file.syslvl.SysMenuFile import SysMenuFile
from lslib.base.file.msrcobj.msobjbase  import RCStringValue
from lslib.base.file.msrcobj.menu       import RCMenu, RCMenuNode, \
                                               RCMenuNodeType

def ConvertMenuXML2CSV(newpath, xmlFile, preloaded=True, autosave=False):
    """A utility function for converting between the XML and CSV versions
    of the System Menu Files. 
    """
    if not preloaded: xmlFile.load()
    csv = SysMenuFileCSV( newpath )
    for proj, menus in xmlFile._projs.items():
        for menu in menus:
            csv.addRCMenu(proj, menu)
    if autosave: csv.save()
    return csv
    

def ConvertMenuCSV2XML(newpath, csvFile, preloaded=True, autosave=False):
    """A utility function for converting between the CSV and XML versions
    of the System Menu Files. 
    """
    if not preloaded: csvFile.load()
    xml = SysMenuFile( newpath )
    for project in csvFile.getProjects():
        xml._projs[project] = csvFile.getProjectMenus( project )
    if autosave: xml.save()
    return xml


class SysMenuFileCSV( LSCSV ):
    """A SysMenuFileCSV is the same as a SysMenuFile, except that its format
    is that of a CSV with sections enabled. To do direct transfers use the 
    helper functions `ConvertMenuXML2CSV` or ConvertMenuCSV2XML` above. Use
    this file object merely as a pass-between to get from TranslationFile(s)
    to System Utility file(s).
    """
    DATA_SECTION_HEADER = "DATA"
    UTIL_SECTION_HEADER = "UTIL"
    PROJ_SECTION_HEADER = "PROJECTS"
    SEPS_SECTION_HEADER = "SEPS"
    
    def __init__(self, path):
        super().__init__( path )
        self.setHasSections()
        # our in-memory section mappings
        self.__projmap = {} # projname -> number
        self.__util    = {} # xpath-id -> (order,type)
        self.__seps    = [] # [ xpath-id ]
        self.__data    = {} # xpath-id -> RCStringValue w/ {langcode->value}
        
        
    def load(self, newpath=None): 
        """Load the SysMenuFileCSV into memory for manipulation."""
        if newpath is not None: self.__path = newpath
        proj, data, util, seps = False, False, False, False
        self.__projmap, self.__util, self.__data, self.__seps = {}, {}, {}, {}
        langcodes = self.getHeader()[1:]
        reader = self.readSection()
        for name, lines in reader:
            if name == SysMenuFileCSV.DATA_SECTION_HEADER:
                self.__loadDataMap( langcodes, lines )
                data = True
            elif name == SysMenuFileCSV.PROJ_SECTION_HEADER:
                self.__loadProjectMap( lines )
                proj = True
            elif name == SysMenuFileCSV.UTIL_SECTION_HEADER:
                self.__loadUtilMap( lines )
                util = True
            elif name == SysMenuFileCSV.SEPS_SECTION_HEADER:
                self.__loadSepsMap( lines )
                seps = True
            else: logging.warning("Found unknown section in SysMenuFileCSV path: %s"%self.__path)
        
        if not (proj and data and util and seps):
            logging.error("SysMenuFileCSV is missing a section in path: %s"%self.__path)
            return False
        
        # we loaded successfully!
        return True
    
    def save(self, newpath=None): 
        """Save the currently loaded SysMenuFileCSV to the specified path."""
        if newpath is not None: self.__path = newpath
        langcodes = self.__getLangCodes()
        header = ['id'] + langcodes
        sections = {
            SysMenuFileCSV.DATA_SECTION_HEADER: self.__getDataLines(langcodes),
            SysMenuFileCSV.PROJ_SECTION_HEADER: self.__getProjectLines(),
            SysMenuFileCSV.UTIL_SECTION_HEADER: self.__getUtilLines()
        }
        writer = self.writeLine(header)
        self.writeSections(sections, writer)
        

    def addProjLine(self, line):
        """Add a line (list) to the project section of the SysMenuFileCSV. This
        function will verify that it is a correct project line before adding 
        it. (i.e., only two columns, the first being a number >= 0).
        """
        if len(line) != 2 or not line[0].isdigit() or int(line[0]) < 0: 
            raise TypeError("Not Project Line")
        self.__loadProjectMap([line])
        
    def addDataLine(self, line):
        """Add a line (list) to the data section of the SysMenuFileCSV. This 
        function will verify that it is a correct data line before adding it.
        (i.e., one or more columns).
        """
        if len(line) < 1: raise TypeError("Not a Data Line")
        self.__loadDataMap(self.__getLangCodes(), [line])

    def addUtilLine(self, line):
        """Add a line (list) to the util section of the SysMenuFileCSV. This
        function will verify that it is a correct util line before adding it.
        (i.e., only three columns, second being a number and the third being
        a valid menu option (e.g., ["SEPARATOR","MENUITEM","POPUP"])).
        """
        if len(line) != 3 or \
           not line[1].isdigit() or \
           int(line[1]) < 0 or \
           line[2].upper() not in ["SEPARATOR","MENUITEM","POPUP"]:
            raise TypeError("Not a Util Line")
        self.__loadUtilMap([line])

    def addRCMenu(self, projname, menu):
        """Recursively delves into a given RCMenu to add it to the
        SysMenuFileCSV. Used in the `ConvertMenuXML2CSV` function above. You 
        should never have to do this by hand.
        """
        if type(menu) is not RCMenu: raise TypeError("Is not Menu!")
        projnum = self._addProject( projname )
        for node in menu._nodes:
            self.__loadViaNode(projnum, node)
        

    def getProjects(self):
        """Returns a list of the projects stored in the File."""
        return list(self.__projmap.keys())

    def getProjectMenus(self, projname):
        """Returns a list of RCMenu objects for the project given."""
        if projname not in self.getProjects():
            raise Exception("Project doesn't exist.")

        progid = self.__projmap[projname]
        relevantUtil, relevantData, relevantSeps = {}, {}, []
        for id, val in self.__util.items():
            try:
                cmpid,newid = id.split('.',1)
                if cmpid == progid: 
                    relevantUtil[newid] = val
            except: pass
        for id, val in self.__data.items():
            try:
                cmpid,newid = id.split('.',1)
                if cmpid == progid: 
                    relevantData[newid] = val
            except: pass
        for sep in self.__seps:
            try:
                cmpid, newid = sep.split('.',1)
                if cmpid == progid:
                    relevantSeps.append(newid)
            except:pass
        # pass it off to the main reconstruction functionality.
        return _ReconstructMenus( relevantData, relevantUtil, relevantSeps )
        

    def _addProject(self, projname):
        maxcount = -1
        for projs, val in self.__projmap.items():
            if projs == projname: return val
            maxcount = max(maxcount, int(val))
        self.__projmap[ projname ] = maxcount+1
        return maxcount+1


    def _getXMLUtilSections(self):
        """Returns the XML UTIL data used in translation files to map the
        rest of the data equally.
        """
        return self.__projmap, self.__util, self.__seps
    def _getXMLDataSection(self):
        """Returns the data section used by this CSV file."""
        return self.__data

    def _setInternals(self, data, projs, util, seps):
        self.__data = data
        self.__projmap = projs
        self.__util = util
        self.__seps = seps

    def __getLangCodes(self):
        lst = {}
        for e in self.__data.values():
            for l in e.getLangCodes(): lst[l]=1
        return list(lst.keys())

    def __getDataLines(self, langcodes):
        lines = []
        for xpathid, val in self.__data.items():
            line = [xpathid]
            for lang in langcodes:
                line.append( val.getValue(lang, '') )
            lines.append(line)
        return lines
    
    def __getProjectLines(self):
        lines = []
        for projname, num in self.__projmap.items():
            lines.append([ str(num),
                           str(projname) ])
        return lines
              
    def __getUtilLines(self):
        lines = []
        for xpathid, val in self.__util.items():
            order, objtype = val
            lines.append([str(xpathid),
                          str(order),
                          str(objtype) ])
        return lines
              
              
    def __loadDataMap(self, langcodes, lines):
        for line in lines:
            if len(line) < 2: continue
            xpathid, *langvals = line
            val = RCStringValue()
            try:
                for lang in langcodes:
                    val.addValuePair(lang, langvals.pop(0))
            except IndexError: pass
            self.__data[ xpathid ] = val
            
    def __loadProjectMap(self, lines):
        for line in lines:
            if len(line) != 2: continue
            number, projname = line
            self.__proj[ projname ] = number
    
    def __loadUtilMap(self, lines):
        for line in lines:
            if len(line) != 3: continue
            idn, order, objtype = line
            self.__util[ idn ] = (order, objtype)
         
    def __loadSepsMap(self, lines):
        for line in lines:
            if len(line) > 1: continue
            self.__seps.append( line[0] )
            
    def __loadViaNode(self, projnum, node):
        idn = "%s.%s"%(projnum, node.getXPath())
        self.__util[ idn ] = (node.orderid, RCMenuNodeType.strType(node.type))
        
        if node.type in RCMenuNodeType.HAS_STRING:
            self.__data[idn] = copy.deepcopy( node.value )
        else: #is separator
            self.__seps.append( idn )
            
        #recurse if we are in a popup    
        if node.type == RCMenuNodeType.POPUP:
            for child in node._children:
                self.__loadViaNode(projnum, child)
    
    
def _ReconstructMenus( data, util, seps ):
    """             ***DO NOT USE THIS FUNCTION DIRECTLY!*** 
    Use `ConvertMenuCSV2XML` as it calls this function through the correct
    conversion process. Reconstructs a list of RCMenus based on flat CSV data 
    in the form of XPaths and ID references. Its tougher to go from CSV back
    to XML than it was to get here. Returns a list of RCMenus.
    """
    #data = { xpath-id -> RCStringValue w/ {langcode->value}}
    #util = { xpath-id -> (order,type)}
    #seps = [ xpath-id ]
    # xpath-id = <menu-name>.<xpath>
    # idn = an id of a menu node
    
    # First expand the utility information into two mappings:
    ordermap = {} # xpath-id -> order (int)
    typemap  = {} # xpath-id -> RCMenuNodeType
    for xpathid, udata in util.items():
        order, typeid = udata
        ordermap[ xpathid ] = int(order)
        typemap [ xpathid ] = RCMenuNodeType.getType(typeid)
     
    # Second, break up the datalines by menuid and by level
    menus    = {} # { menuid -> { xpath-id -> value } }
    menulvls = {} # { menuid -> { lvl -> [xpath-id] } }
    for xpathid, value in data.items():
        menuid, xpath = xpathid.split('.', 1)
        lvl = _determineXPathLvl(xpath)
        if menus.get(menuid) is None: menus[menuid] = {}
        if menulvls.get(menuid) is None: menulvls[menuid] = {}
        if menulvls[menuid].get(lvl) is None: menulvls[menuid][lvl] = []

        menus[menuid][xpath] = value
        menulvls[menuid][lvl].append(xpath)
        
    #Third, add all the separaters to the menus and the menulvls maps.
    for sep in seps:
        menuid, xpath = sep.split('.',1)
        lvl = _determineXPathLvl(xpath)
        if menus.get(menuid) is None: menus[menuid] = {}
        if menulvls.get(menuid) is None: menulvls[menuid] = {}
        if menulvls[menuid].get(lvl) is None: menulvls[menuid][lvl] = []

        menus[menuid][xpath] = None
        menulvls[menuid][lvl].append(xpath)
        
    # Finally, for each menu in `menus`, loop by level adding the top 
    #    level first, and by order.
    menulst = [] #what gets returned!
    for menuid in menus:
        menu = RCMenu(menuid)
        for lvl in menulvls[menuid]:
            lvlorder = {} # order (int) -> xpath
            
            # loops through all the xpaths at this lvl and determines
            # the order to add them by adding them to the lvlorder
            # dictionary, which auto-sorts them.
            for txpath in menulvls[menuid][lvl]:
                orderid = ordermap[ menuid+"."+txpath ]
                if lvlorder.get( orderid ) is None:
                    lvlorder[ orderid ] = [txpath]
                else: lvlorder[ orderid ].append( txpath )
                
            # Now that we have what order to add them to the menu.
            # We loop through all the items at this level, and add them
            # by asking the menu to find the parent based on the xpath.
            for orderid, txpaths in sorted(lvlorder.items(), key=lambda x: x[0]):
                for txpath in txpaths:
                    idn = _determineBasename(txpath)
                    typeid = typemap[menuid+"."+txpath]
                    if typeid == RCMenuNodeType.POPUP:
                        node = RCMenuNode(menu,type=typeid,idn=idn,order=orderid)
                        node.value.combine( menus[menuid][txpath],suppressIDWarn=True )
                        parent = menu.findParentOfNode( txpath )
                        if parent is not None:
                            parent.addChild( node )
                    elif typeid == RCMenuNodeType.MENUITEM:
                        node = RCMenuNode(menu,id=idn,type=typeid,order=orderid)
                        node.value.combine( menus[menuid][txpath],suppressIDWarn=True )
                        parent = menu.findParentOfNode( txpath )
                        if parent is not None:
                            parent.addChild( node )
                    elif typeid == RCMenuNodeType.SEPARATOR:
                        node = RCMenuNode(menu,type=typeid,idn=idn,order=orderid)
                        parent = menu.findParentOfNode( txpath )
                        if parent is not None:
                            parent.addChild( node )
                    else: continue #TODO: log? this is an invalid type!
        # Now we can add that menu to the list of menus to return.            
        menulst.append(menu)
    return menulst


def _determineXPathLvl( xpath ):
    """Finds how many recursive levels down the xpath goes."""
    return len(xpath.split('.'))

def _determineBasename( xpath ):
    """Finds the end identifier of the xpath (synonymous with os.basename)."""
    try:    return xpath.split('.')[-1]
    except: raise Exception("no splits able!")