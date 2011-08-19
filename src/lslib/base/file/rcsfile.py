#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""This is a special type of file for Visual Studio projects, we would like to
be able to grab out pretty much everything this file stores along with 
combine them, change them, view them, reproduce them in other forms, etc.

This file is very RegEx heavy, which means DON'T CHANGE ANYTHING UNLESS YOU
KNOW WHAT YOU ARE DOING!!! All RegEx strings have gone through testing and have
been verified to work in all cases we can come up with. If there are 
optimizations, please verify on all RC files that the utility files created are
the exact same.

LATER:
   - reading RCT files (templates)
   - improve generalization. Currently this is fairly project specific.
"""

import re                 
import logging            #@UnusedImport
import fileinput
import os.path as ospath

from lslib.base.file.msrcobj.menu        import * #@UnusedWildImport
from lslib.base.file.msrcobj.dialogex    import * #@UnusedWildImport
from lslib.base.file.msrcobj.stringtable import * #@UnusedWildImport


def scanRCFile( rcpath, hpath=None, defaultLang='1033' ):
    """Scans a file and tries to determine if its a valid RCS file. If it is
    then it will return the RCSFile object. Otherwise it will return None.
    It also checks what the language code of the rc file is too.
    """
    file,langcode = ospath.basename(rcpath),defaultLang
    file = file[:file.index(".")]
    if "_" in file: 
        langcode=file[file.rindex("_")+1:]
        try: int(langcode)
        except: langcode=defaultLang
        name = file[:file.rindex("_")]
    else: name = file
    #LATER: if this filename check didn't work ACTUALLY scan the file.
    return RCSFile( rcpath, hpath, langcode, name )
    
    

###############################################################################
# Our RegEx matchers for Menus, Dialogs, and String tables. There are two for 
# each because the first is for quick matching, and the second is for two line
# matching to make certain we are in the right location.                      
###############################################################################
MENU_MATCHER    = re.compile("^[A-Z]{2,3}_[A-Z_]+\sMENU[ ]*$")
MENU_MATCHER2   = re.compile("^[A-Z]{2,3}_[A-Z_]+\sMENU[ ]*(\n|\r\n)BEGIN[ ]*$")
DIALOG_MATCHER  = re.compile("^[A-Z]{2,3}_[A-Z_]+\sDIALOGEX(\s+[0-9]+,?){4}$")
DIALOG_MATCHER2 = re.compile("^[A-Z]{2,3}_[A-Z_]+\sDIALOGEX(\s+[0-9]+,?){4}(\n|\r\n)STYLE(\s+[A-Z]{2,3}_[0-9a-zA-Z_]+\s+\|?)*$")
STRTBL_MATCHER  = re.compile("^STRINGTABLE[ ]*$")
STRTBL_MATCHER2 = re.compile("^STRINGTABLE[ ]*(\n|\r\n)BEGIN[ ]*$")
END_BLOCK_MATCH = re.compile("^\s*END[ ]*$")
LAST_END_BLOCK_MATCHER = re.compile("^END[ ]*$")

###############################################################################
# Internal elements of the Menus, dialogs, and String tables used for 
# verification. 
###############################################################################
MENU_ITEM_2LINE    = re.compile('^\s+MENUITEM[ ]*"(.*?)",[ ]*$')
MENU_ITEM_MATCHER  = re.compile('^\s+MENUITEM[ ]*"(.*?)",\s*([A-Z]{2,3}_[0-9a-zA-Z_]+)\s*$')
MENU_ITEM_MATCHER2 = re.compile('^\s+MENUITEM[ ]*"(.*?)",\s*([0-9]+)\s*$') #missing ID
POPUP_MATCHER     = re.compile('^\s+POPUP\s"(.*?)"$')
SEPARATOR_MATCHER = re.compile('^\s+MENUITEM\sSEPARATOR[ ]*$')
DIALOG_BEGIN_MATCHER  = re.compile('^BEGIN[ ]*$')
DIALOG_2LINE_ENTITY   = re.compile('^\s+[A-Z]+\s+".*?",[\n\r]{1,2}$')
DIALOG_ENTITY_MATCHER = re.compile('^\s+[A-Z]+\s+"(.*?)",\s*?([A-Z]{2,3}_?[0-9a-zA-Z_]+),')
DIALOG_STATIC_MATCHER = re.compile('^\s+[A-Z]+\s+"(.*?)",\s*?(\-1,"Static"|IDC_STATIC),')
STRTBL_LINE_MATCHER  = re.compile('^\s+([A-Z]{2,3}_[0-9a-zA-Z_]+)\s+"(.*?)"$')
STRTBL_ID_UNSTANDARD_MATCHER = re.compile('^\s+([0-9a-zA-Z_]+)\s+"(.*?)"$')
STRTBL_2LINE_MATCHER = re.compile('^\s+([A-Z]{2,3}_[0-9a-zA-Z_]+)\s?$')    
   
   
def make_val_safe( val ):
    """This is essentially a magic quotes function. RC files can have double
    quotes in the values, but in order to not break everything it needs to be
    doubled, ie 'He said, "Hello World".' needs to be 
    'He said, ""Hello World"".'
    
    This function should only be called on values that have already been made
    normal by the function below. Otherwise you may wind up with too many 
    quotes.
    """
    return str(val).replace('"','""')

def make_val_normal( val ):
    '''The opposite of `make_val_safe`. This removes the extra quotes around 
    it. A problem might occur with a string like: 'He said, "".' But since this
    function is only being called on strings pulled from an rcs file, you'll 
    only get strings like: 'He said, """".'
    '''
    return str(val).replace('""','"')
    
class RCSFile:
    """This is a standard resource file for Visual Studio, it can be used for
    parsing as well as pushing and pulling from them. Make sure to give both
    the path of the resource.h file and the <project name>.rc file.
    """
    def __init__(self, path, header, langcode, projname=None):
        self._langcode   = langcode
        self._headerfile = header
        self._path       = path
        self._name       = projname
        self._defaultLangcode = '1033' #LATER: pull this out!
        
    def pullMenu(self):
        """Use this function as an iterator as it will scan through the file 
        and pull out the menu tables into RCMenu objects. You can then pass 
        those menus to RCMenuFiles or just utilize them right then.  
        """
        global MENU_MATCHER, MENU_MATCHER2 # Our RegEx for finding menus
        global MENU_ITEM_MATCHER, POPUP_MATCHER, SEPARATOR_MATCHER # Menu items
        global END_BLOCK_MATCH # Used for both eo Menu and eo PopUp
        
        reader = self.__readline()
        while True:
            line, reader = self.__readTilMatch(MENU_MATCHER, reader)
            
            if line is None: break # There arn't any more menus in this rc
            else: line+=next(reader)
            
            # Quick double check we are in the right place before parsing further.
            if MENU_MATCHER2.search(line) is None: continue
    
            menu = RCMenu( line[:line.index(" ")] ) # grab id and make menu obj
            
            # OK now we can start reading and parsing!
            inPopup = False
            curPopup = None
            order=0
            for line in reader:
                order+=1
                if MENU_ITEM_2LINE.search( line ) is not None:
                    line+=next(reader)
                
                ## If it matches a standard menu item, then we need to 
                ## pull out the ID and String and save it into the menu.
                if MENU_ITEM_MATCHER.search( line ) is not None:
                    # determine the id and the value of the node.
                    nodeId, nodeVal, res  = '', '', MENU_ITEM_MATCHER.search(line).groups()
                    try: 
                        #nodeId = line.split(" ")[-1].strip()
                        nodeId = res[1]
                    except:
                        logging.error("Couldn't determine menu item's id when reading from rc:%s"%line)
                        continue
                    try: 
                        #tmp = line.split("MENUITEM")[1].strip()
                        #nodeVal = tmp[1:tmp.rfind("\", ",0)]
                        nodeVal = make_val_normal(res[0])
                    except Exception as e:
                        logging.error("Couldn't determine menu item's value when reading from rc:%s"%line)
                        logging.exception(e)
                        continue
                    
                    #make node and add it!  
                    node = RCMenuNode(menu, id=nodeId, order=order)
                    node.value.addValuePair(self._langcode, nodeVal)
                    if inPopup: curPopup.addChild( node )
                    else: menu._nodes.append( node )
                
                ## If it matches a PopUp then we need to set our state as
                ## sub-PopUp, and then start filling it all out.
                elif POPUP_MATCHER.search( line ) is not None:
                    node = RCMenuNode(menu, type=RCMenuNodeType.POPUP, order=order)
                    nodeVal, res = '', POPUP_MATCHER.search( line ).groups()
                    try: 
                        #nodeVal = line.split("POPUP")[-1].strip()[1:-1]
                        nodeVal = make_val_normal(res[0])
                    except:
                        logging.error("Couldn't determine popup's value when reading from rc:%s"%line)
                        # This is bad but we can't ignore it as we would
                        # loose all internals. So lets try to continue.
                    
                    if nodeVal is None: nodeVal=''
                    node.value.addValuePair(self._langcode, nodeVal)
                    if inPopup: curPopup.addChild(node)
                    else: inPopup = True
                    curPopup = node
                    ## push the current reader!
                    next( reader ) #pushes it past the "BEGIN"
                    
                ## If its a separator just add it to the current menu/PopUp.
                elif SEPARATOR_MATCHER.search( line ) is not None:
                    node = RCMenuNode(menu, type=RCMenuNodeType.SEPARATOR, order=order)
                    if inPopup: curPopup.addChild(node)
                    else: menu._nodes.append( node )
                    
                ## If its an end block we need to check if we yield the menu,
                ## or if we are inside a PopUp block, then we need to add the
                ## PopUp to the current menu.
                elif END_BLOCK_MATCH.search( line ) is not None:
                    order-=1#just to make sure we arn't skipping one.
                    if inPopup:
                        # we are still in a PopUp just now we need to jump out
                        # into the previous parent PopUp.
                        if curPopup._parent is not None:
                            curPopup = curPopup._parent
                        else:
                            menu._nodes.append( curPopup )
                            inPopup = False
                            curPopup = None
                    else:
                        yield menu
                        break
                elif MENU_ITEM_MATCHER2.search( line ) is not None:
                    # determine the id and the value of the node.
                    nodeNum, nodeVal, res  = '', '', MENU_ITEM_MATCHER2.search(line).groups()
                    try: 
                        #nodeNum = line.split(" ")[-1].strip()
                        nodeNum = res[1]
                    except:
                        logging.error("Couldn't determine menu item's id when reading from rc:%s"%line)
                        continue
                    try: 
                        #tmp = line.split("MENUITEM")[1].strip()
                        #nodeVal = tmp[1:tmp.rfind("\", ",0)]
                        nodeVal = make_val_normal(res[0])
                    except Exception as e:
                        logging.error("Couldn't determine menu item's value when reading from rc:%s"%line)
                        logging.exception(e)
                        continue
                    
                    #make node and add it! 
                    node = RCMenuNode(menu, id=RCValueID(None,nodeNum), order=order) #we have to hack around it.
                    node.value.addValuePair(self._langcode, nodeVal)
                    if inPopup: curPopup.addChild( node )
                    else: menu._nodes.append( node )
                
                ## We have no idea what this line is. Lets log it but we should continue
                ## for the sake of trying to be as complete as possible. This is bad that
                ## we didn't know what the line was. We should probably have a PopUp or 
                ## something.
                else: 
                    if line.strip() != "": logging.warning("When parsing for menu, line didn't match any possible: %s"%line)
            
    def pullDialog(self):
        """Use this function as an iterator as it will scan through the file
        and pull out the dialog tables into RCDialog objects. You can then
        pass those dialogs to RCDialogFiles or just utilize them right then.
        """
        global DIALOG_MATCHER, DIALOG_MATCHER2 # Our RegEx for finding dialogs
        global DIALOG_BEGIN_MATCHER, DIALOG_ENTITY_MATCHER # Matching strings
        global END_BLOCK_MATCH # Making sure we hit our ending.
        
        reader = self.__readline()
        while True:
            line, reader = self.__readTilMatch(DIALOG_MATCHER, reader)
            
            if line is None: break # There arn't any more dialogs in this rc
            else: line+=next(reader)
            
            # Quick double check we are in the right place before parsing further.
            if DIALOG_MATCHER2.search(line) is None: continue
            dialog = RCDialog(line[:line.index(' DIALOGEX')])
            
            #Find the beginning of the entries.
            line, reader = self.__readTilMatch(DIALOG_BEGIN_MATCHER, reader)
            
            for line in reader:
                ## Sometimes static strings can get HUGE, so we have to be able to still recognize them.
                if DIALOG_2LINE_ENTITY.search(line) is not None:
                    line=line.rstrip('\n')+next(reader)
                
                ## We found an entity, so lets grab its value and id!
                if DIALOG_ENTITY_MATCHER.search(line) is not None:
                    
                    #Check first to see if its static.
                    if DIALOG_STATIC_MATCHER.search(line) is not None:
                        res = DIALOG_STATIC_MATCHER.search(line).groups()
                        try: entityVal = make_val_normal(res[0])
                        except:
                            logging.warning("Couldn't determine entity value when pulling dialog from rc: %s"%line)
                            continue
                    
                        value = RCStringValue( "IDC_STATIC" )
                        value.addValuePair(self._langcode, entityVal)
                        dialog.addValue( value, static=True )
                        
                    else:
                        entityVal, entityId, res = '', '', DIALOG_ENTITY_MATCHER.search(line).groups()
                        
                        try: entityVal = make_val_normal(res[0])
                        except:
                            logging.warning("Couldn't determine entity value when pulling dialog from rc: %s"%line)
                            continue
                        
                        try: entityId = res[1]
                        except:
                            logging.warning("Couldn't determine entity id when pulling dialog from rc: %s"%line)
                            continue
                        
                        value = RCStringValue( entityId )
                        value.addValuePair( self._langcode, entityVal )
                        dialog.addValue( value )
                
                ## If we reached the end of the block, lets break out of here.
                elif END_BLOCK_MATCH.search(line) is not None: break
                
                ## if we don't know what it is, most likely its a a 
                ## continuation of an entity that we don't care about. But lets
                ## explicitly state that:
                else: continue
            
            ## Now that we filled our dialog object, lets return it
            yield dialog
            
    def pullStringTable(self):
        """Use this function as an iterator as it will scan through the 
        file and pull out the string tables into RCStrTbl objects. It 
        will not combine them (as they probably should be) because its
        a simple thing to do on your own.  
                        'RCStrTbl.addStringTable( table )'
        """
        global STRTBL_MATCHER, STRTBL_MATCHER2
        global STRTBL_LINE_MATCHER, STRTBL_2LINE_MATCHER 
        global STRTBL_2LINE_STR_MATCHER, END_BLOCK_MATCH
        
        reader = self.__readline()
        while True:
            line, reader = self.__readTilMatch(STRTBL_MATCHER, reader)
            
            if line is None: break # There arn't any more dialogs in this rc
            else: line+=next(reader)
            
            # Quick double check we are in the right place before parsing further.
            if STRTBL_MATCHER2.search(line) is None: continue
            
            table = RCStrTbl()
            for line in reader:
                
                ## Recognized that this line is a value, but that its 
                ## broken up onto 2 lines. Lets grab the next line and
                ## concatenate it to the end of the current one.
                if STRTBL_2LINE_MATCHER.search(line) is not None:
                    line += next( reader )
                
                
                ## We matched a line, lets add it to the table.
                if STRTBL_LINE_MATCHER.search(line) is not None:
                    val, id, res = '', '', STRTBL_LINE_MATCHER.search(line).groups()
                    try: id = res[0]
                    except:
                        logging.error("Couldn't determine entity id when pulling dialog from rc: %s"%line)
                        break
                    strVal = RCStringValue(id)
                    
                    try: val = make_val_normal(res[1])
                    except:
                        logging.error("Couldn't determine entity value when pulling dialog from rc: %s"%line)
                        break
                    strVal.addValuePair(self._langcode, val)
                    
                    table.addStringValue( strVal )
                    
                    
                ## There is a problem with reading the ID. It might either not have 
                ## a define in the header file, or its ID might be unstandard.
                elif STRTBL_ID_UNSTANDARD_MATCHER.search(line) is not None:
                    val, id, res = '', '', STRTBL_ID_UNSTANDARD_MATCHER.search(line).groups()
                    try: id = make_val_normal(res[0])
                    except:
                        logging.error("Couldn't determine entity id when pulling dialog from rc: %s"%line)
                        break
                    logging.error("There was an non-standard ID found in the string table which will not be maintained: %s"%id)
                    
                ## We found the end of the string table block. Lets just break
                ## out and continue onto the next table.
                elif END_BLOCK_MATCH.search(line) is not None: break
                
                ## If we don't know what the line is, thats a problem. But
                ## We will consider it a line bug and just break out of that
                ## string table.
                else: 
                    logging.warning("Found a line that doesn't match filters: %s"%line)
                    break
            yield table
            
            
    def __readline(self):
        ### Used for reading the file line by line so we can do parsing. ###
        ### @return: A Generator, pulls our lines for matching.
        reader = fileinput.FileInput([self._path], mode="r")
        for line in reader: yield line

    def __readTilMatch(self, matcher, reader=None, buffer=None, curline=0, matchIndent=False):
        ### Reads the file until there is a match
        ### @return: a tuple of the matched line and the current line generator
        if buffer is None:
            if reader is None: reader = self.__readline()
            for line in reader: 
                if matcher.search( line ) is not None:
                    return (line, reader)
        else:
            for linenum, line in buffer.items():
                if linenum <= curline: continue
                if matcher.search(line) is not None:
                    if matchIndent:
                        originalIndent = len(buffer[curline]) - len(buffer[curline].lstrip())
                        if originalIndent != (len(line) - len(line.lstrip())): continue
                    return (line, linenum)
        return (None, None)
            
    def __readIntoBuffer(self):
        buffer = {}
        lines  = self.__readline()
        linecount = 0
        for line in lines: 
            buffer[linecount] = line
            linecount+=1
        return buffer
    
    def __saveBuffer(self, buffer):
        with open(self._path, 'w') as rcs:
            for _, line in sorted(buffer.items(),key=(lambda x: x[0])):
                rcs.write( line )
    
    
    def updateMenus(self, menuFile, preloaded=True, save=True, retBuffer=True, buffer=None, smartOverlap=True):
        """ Updates the menus from a language/project level menu file in this 
        RCS file.
        """
        global MENU_ITEM_MATCHER, POPUP_MATCHER, MENU_ITEM_MATCHER2
        myBuff = buffer
        if myBuff is None: myBuff = self.__readIntoBuffer()
        if not preloaded: menuFile.load()
        
        for menu in menuFile._menus:
            menulines = menu.asRCString(langcode=self._langcode, aslist=True)
            menusize = len(menulines)
            if menusize < 2: continue
            linenum, limit = 0, -1
            while True:
                line, linenum = self.__readTilMatch(MENU_MATCHER, buffer=myBuff, curline=linenum)
                if line is None: break  # we reached the end of the buffer. No match
                elif line == menulines[0]: # found match, lets start editing.
                    _,limit = self.__readTilMatch(LAST_END_BLOCK_MATCHER, buffer=myBuff, curline=linenum)
                    
                    if limit-linenum == len(menulines)-1:
                        prev_linenum, prev_buffer = linenum, myBuff
                        for menuline in menulines: # menu search loop
                            if myBuff[linenum] == menuline: 
                                linenum+=1
                                continue
                            
                            # If both are menu items
                            if MENU_ITEM_MATCHER.search( myBuff[linenum] ) is not None and \
                               MENU_ITEM_MATCHER.search( menuline ) is not None:
                                myBuff[linenum] = menuline
                                linenum+=1
                                
                            # If both are pop up headers
                            elif POPUP_MATCHER.search( myBuff[linenum] ) is not None and \
                               POPUP_MATCHER.search( menuline ) is not None:
                                myBuff[linenum] = menuline
                                linenum+=1
                                
                            # If there is a menu item that is missing an id.
                            elif MENU_ITEM_MATCHER2.search( myBuff[linenum] ) is not None and \
                               MENU_ITEM_MATCHER2.search( menuline ) is not None:
                                myBuff[linenum] = menuline
                                linenum+=1
                                
                            # Otherwise we have a problem, there is a mismatch in the menu
                            # generated. We have to use smart-overlap.
                            else:
                                logging.error("!- Failed on:\n%s\n%s\n!-------"%(repr(myBuff[linenum]),repr(menuline)))
                                response = "Attempting smart overlap." if smartOverlap else "Smart Overlap is off, so skipping menu."
                                logging.warning("Menu Structure is (%d,%d) different for %s! %s"%((limit-linenum),len(menulines),str(menu.id),response))
                                logging.debug("New Menu Structure Generated:\n%s"%menulines)
                                if smartOverlap: linenum, myBuff = self.__smartMenuOverlap(prev_buffer, prev_linenum, limit, menu)
                                else: linenum, myBuff = prev_linenum, prev_buffer
                                break # get out of menu search loop
                    else:
                        response = "Attempting smart overlap." if smartOverlap else "Smart Overlap is off, so skipping menu."
                        logging.warning("Menu Structure is (%d,%d) different for %s! %s"%((limit-linenum),len(menulines),str(menu.id),response))
                        logging.debug("New Menu Structure Generated:\n%s"%menu.asRCString(langcode=self._langcode))
                        if smartOverlap: linenum, myBuff = self.__smartMenuOverlap(myBuff, linenum, limit, menu)
                    #We attempted to merge, the found menu. Lets continue to 
                    # the next menu in the list.
                    break
        if save: self.__saveBuffer(myBuff)
        if retBuffer: return myBuff
        
    def __smartMenuOverlap(self, buffer, startIndex, realEndIndex, menu):
        global MENU_ITEM_MATCHER, MENU_ITEM_2LINE, \
               MENU_ITEM_MATCHER2, POPUP_MATCHER, END_BLOCK_MATCH
        
        newBuff = buffer
        # Smart overlap is essentially what string tables has to do
        # which is scan until you find the ID of the string you need
        # and then pull it out of the menu.
        linenum = startIndex
        while linenum < realEndIndex:
            line = newBuff[linenum]
            # if its a pop-up matcher, lets make sure the lines internal
            # to it have the same IDs as a child in one of the popups
            # recorded in the menu object.
            if POPUP_MATCHER.search(line) is not None:
                # Find the end of the pop-up so we can scan through to find IDs
                _,popupEndIndex = self.__readTilMatch(END_BLOCK_MATCH, buffer=newBuff, curline=linenum, matchIndent=True)
                
                # Find the parent's ID, of all internal MenuNodes
                unsafe_error = False 
                pids = {}
                mitemCount = 0
                inSubPopup = 0 # 0=False, >0=how sub we are
                for index in range(linenum+1, popupEndIndex):
                    tmpline = newBuff[index]
                    if END_BLOCK_MATCH.search(tmpline) is not None:
                        inSubPopup-=1
                        if inSubPopup < 0: 
                            logging.error("You have a malformed Menu '%s' in: %s"%(str(menu.id), self._path))
                            unsafe_error = True
                            break
                    elif POPUP_MATCHER.search(tmpline) is not None:
                        inSubPopup+=1
                    elif MENU_ITEM_MATCHER.search(tmpline) is not None or \
                         MENU_ITEM_MATCHER2.search(tmpline) is not None:
                        #find id based on SubPopup
                        mitemCount+=1
                        try: res = MENU_ITEM_MATCHER.search(tmpline).groups()
                        except: res = MENU_ITEM_MATCHER2.search(tmpline).groups()
                        try:logging.debug("trying to find: %s, found %s"%(res[1], menu.getChild(res[1]).getXPath()))
                        except: logging.debug("trying to find: %s, found NONE"%res[1])
                        mitem = menu.getChild(res[1])
                        for _ in range(inSubPopup):
                            try: mitem = mitem._parent
                            except: break
                        try:
                            pid = str(mitem.getIdentifier())
                            if pid in pids: pids[pid]+=1
                            else: pids[pid]=1
                        except: continue
                
                # Too many ENDs and not enough POPUPS        
                if unsafe_error: 
                    linenum+=1#skip that line.
                    continue
                elif len(pids) == 0:
                    linenum+=1#skip that line.
                    logging.warning("Unable to find any menu items in a popup, this could mean a malformed menu!")
                    continue
                 
                if len(pids.keys()) == 1: pid = list(pids.keys())[0]
                else:
                    # Compares the frequency of PID usage in the sub
                    # popups. if there was No concensus (ie there was
                    # only one or two off on all the others), then
                    # we have no choice but to say there was an error.
                    factor = 2 if mitemCount > 2 else 1
                    pids = sorted(list(filter(lambda x:x[1]>factor, pids.items())), key=lambda x:x[1])
                    try: 
                        pid = pids[-1][0]
                        logging.debug("SmartOverlap: Found multiple locations with similar ID patterns. Taking most likely.")
                    except:
                        logging.warning("SmartOverlap: Could not find the value for a popup menu in "+
                                        "%s, couldn't even guess id."%str(menu.id))
                        linenum+=1#skip that line.
                        continue
                 
                # now that we have the parent's id we can grab the 
                # node from the menu and get its value to exchange.
                child = menu.getChild( pid ) #the id
                if child is not None: # we found the value!
                    val = child.value.getValue(self._langcode)
                    if val is None or val == '':
                        val = child.value.getValue(self._defaultLangcode,'')
                    newBuff[linenum] = '%s"%s"%s'%(line[:line.index('"')],
                                                   make_val_safe(val),
                                                   line[line.rindex('"')+1:])
                else:
                    # we couldn't find the popup menu's value
                    # so we have to skip it and leave it blank.
                    logging.warning("SmartOverlap: Couldn't find the value for a popup menu in %s,"+
                                    " guessed id=%s"%(str(menu.id), pid))
            # Grab the ID and search the menu for a like id, if one is found
            # then edit the line, otherwise we need to log a warning.
            elif MENU_ITEM_MATCHER.search(line) is not None or \
                 MENU_ITEM_MATCHER2.search(line) is not None:
                try: res = MENU_ITEM_MATCHER.search(line).groups()
                except: res = MENU_ITEM_MATCHER2.search(line).groups()
                child = menu.getChild( res[1] ) #the id
                if child is not None: # we found the value!
                    val = child.value.getValue(self._langcode)
                    if val is None or val == '':
                        val = child.value.getValue(self._defaultLangcode,'')
                    newBuff[linenum] = '%s"%s"%s'%(line[:line.index('"')],
                                                   make_val_safe(val),
                                                   line[line.rindex('"')+1:])
                else:    
                    # We couldn't find the id in the menu. This means
                    # that either, A. we don't have the right menu, or
                    # B. the saved menu is incomplete. Either way the 
                    # only way we can cope is to display a warning in 
                    # the log.
                    logging.warning("SmartOverlap: Couldn't find ID: %s, in %s."%(res[1], str(menu.id)))
                
            # If we match a two line menu item, lets grab the id from the 2nd 
            # line and treat it like we would a single line.
            elif MENU_ITEM_2LINE.search(newBuff[linenum]) is not None:
                linenum+=1 #increment the current position
                tmpline = line + newBuff[linenum] # add the cur line to the present.
                
                res = MENU_ITEM_MATCHER.search(tmpline).groups()
                child = menu.getChild( res[1] ) #the id
                if child is not None: # we found the value!
                    val = child.value.getValue(self._langcode)
                    if val is None or val == '':
                        val = child.value.getValue(self._defaultLangcode)
                    newBuff[linenum-1] = '%s"%s"%s'%(line[:line.index('"')],
                                                   make_val_safe(val),
                                                   line[line.rindex('"')+1:])
                else:    
                    # We couldn't find the id in the menu. This means
                    # that either, A. we don't have the right menu, or
                    # B. the saved menu is incomplete. Either way the 
                    # only way we can cope is to display a warning in 
                    # the log.
                    logging.warning("SmartOverlap: Couldn't find ID: %s, in %s."%(res[1], str(menu.id)))
            
            #Go to next line
            linenum+=1
        
        return realEndIndex, newBuff
        
    def updateStringTables(self, stringsFile, preloaded=True, save=True, retBuffer=True, buffer=None):
        """Updates the string tables from a language/project level string 
        table file in this RCS file.
        """
        myBuff = buffer
        if myBuff is None: myBuff = self.__readIntoBuffer()
        if not preloaded: stringsFile.load()
        
        linenum = 0
        while True:
            line, linenum = self.__readTilMatch(STRTBL_MATCHER, buffer=myBuff, curline=linenum)
            if line is None: break
            else: linenum+=1
            
            while True:
                linenum+=1
                line = myBuff[linenum]
                if END_BLOCK_MATCH.search(line) is not None: break
                elif STRTBL_LINE_MATCHER.search(line) is not None:
                    res = STRTBL_LINE_MATCHER.search(line).groups()
                    newval = stringsFile.getValue(res[0], langcode=self._langcode)
                    if newval is None or newval == '': 
                        newval = stringsFile.getValue(res[0], langcode=self._defaultLangcode)
                        if newval is None: #TODO: run header scan to get possible values!
                            logging.warning("Given file %s does not have correct langcode '%s' to update %s"%(stringsFile._path,self._langcode,self._path))
                            continue
                    myBuff[linenum] = '%s"%s"\n'%(line[:line.index('"')],make_val_safe(newval))
                elif STRTBL_2LINE_MATCHER.search(line) is not None:
                    res = STRTBL_2LINE_MATCHER.search(line).groups()
                    newval = stringsFile.getValue(res[0], langcode=self._langcode)
                    if newval is None or newval == '': #TODO: run header scan to get possible values!
                        newval = stringsFile.getValue(res[0], langcode=self._defaultLangcode)
                        if newval is None: #still none, TODO: the key might be bad, go check header 
                            logging.warning("Could not find a value for %s in %s's string table"%(res[0],self._name))
                            continue
                    linenum+=1
                    line = myBuff[linenum] 
                    myBuff[linenum] = '%s"%s"\n'%(line[:line.index('"')],make_val_safe(newval))
        if save: self.__saveBuffer( myBuff )
        if retBuffer: return myBuff    
        
    def updateDialogs(self, dialogFile, preloaded=True, save=True, retBuffer=True, buffer=None):
        """Updates the dialogs from a language/project level dialog file in
        this RCS file.
        """
        myBuff = buffer
        if myBuff is None: myBuff = self.__readIntoBuffer()
        if not preloaded: dialogFile.load()
        
        linenum = 0
        while True:
            line, linenum = self.__readTilMatch(DIALOG_MATCHER, buffer=myBuff, curline=linenum)
            if line is None: break
            else: linenum+=1
            
            # grab dialog
            staticcount=0
            did = line[:line.index(' DIALOGEX')]
            dialog = None
            for dlog in dialogFile._dialogs:
                if did==dlog.id: 
                    dialog = dlog
                    break
            if dialog is None: continue
            
            # loop through dialog lines and match to values
            while True:
                linenum+=1
                if linenum > len(myBuff): break
                line = myBuff[linenum]
                if END_BLOCK_MATCH.search(line) is not None: break
                elif DIALOG_ENTITY_MATCHER.search(line) is not None: 
                    oldval = '"%s",'%DIALOG_ENTITY_MATCHER.search(line).groups()[0]
                    # If the item is a static, we need to check the current static count,
                    # and pull out the right value.
                    if DIALOG_STATIC_MATCHER.search(line) is not None:
                        id = "IDC_STATIC.%d"%staticcount
                        staticcount+=1
                    else: id = DIALOG_ENTITY_MATCHER.search(line).groups()[1]
                    
                    newval = dialog.getValue( id, langcode=self._langcode )
                    if newval is None or newval == '': 
                        newval = dialog.getValue(id, langcode=self._defaultLangcode)
                        if newval is None: #still none, TODO: the key might be bad, go check header 
                            logging.warning("Could not find a value for %s in %s's dialog: %s"%(id,self._name,did))
                            continue
                    
                    fst = line[:line.index('"')]
                    snd = line[len(fst+oldval):]
                    newline = '%s"%s",%s'%(fst,make_val_safe(newval),snd)
                    
                    myBuff[linenum] = newline
                    
        if save: self.__saveBuffer( myBuff )
        if retBuffer: return myBuff
        
        
    def save(self, newpath, newbuffer=None):
        """ Saves a copy of the RCS file to a new location, or saves a new
        buffered file to the new path instead.
        """
        if newbuffer is None:
            buff = self.__readIntoBuffer()
        else:
            buff = newbuffer
        self._path = newpath
        self.__saveBuffer( buff )
        