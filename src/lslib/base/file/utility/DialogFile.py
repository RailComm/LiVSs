#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
""" A DialogFile (*.dialogs) is a file that contains one or more dialog that 
are used within a given project. What is good about a dialog file is that a  
single dialog can contain all of its language/resource data so that it can be 
exported to multiple (or preferably ALL) of your resource files.

The Format of a dialog file is as follows:
                            [HEADER]
                            [SECTION]
                            [ENTRY]
                            [ENTRY]
                            ...
                            [NEWLINE]
                            [SECTION]
                            [ENTRY]
                            ...
                            [NEWLINE]
                            ...
Each of these [*] represents a line in the file. The description of each line 
is next:

Newline - This is just a new line as represented by a carriage return (\r\n).

Section - This is a section header as described by the HSCSV file type, it is
        the name of the dialog that contains all entries below. If the section
        has no entries, the section line may be omitted but its not required.

Header - This is the line that may change in the future; but it defines what 
        each column represents. See below.
        
Entry - A control in the dialog that is maintained via an RCDialog object. 
        Its form matches the header.
        
The following is the definition of the header's columns and their position
    
                        id,langcode1,langcode2,...
id - the id of the Entry (the control entity ie IDC_BYLOCATIONCHECK, etc).

langcode# - this is substituted with the actual language code. To make the 
        columns look similar to: 'id,1033,2058'. This may be changed later
        to make it more readable (ie '1033-en-US', but what these columns 
        represent will never change.

This file is severely reduced from its imagined capabilities. it could hold 
much more information (eg, position of control entity, what features are
enabled, its type, etc). All that would really need to change is the columns.
What we'd have to do is change the 'CONTROL_COLS' to indicate how many of the
columns in the front there HAS to be. Then all the others will be langcodes.
An example of this would be:
    if CONTROL_COLS = 7:
    cols = 'id,type,xloc,yloc,width,height,settings,1033-enUS,2058-esMX'
"""

from lslib.base.file.lscsv import LSCSV
from lslib.base.file.msrcobj.dialogex import RCDialog
from lslib.base.file.msrcobj.msobjbase import RCStringValue


def ScanDialogFile( dialogFile, headerLst ):
    """Scan through the headers and make sure the file is correct."""
    from lslib.base.file.rchfile import findElemNumInGroup
    def _scanNodeList( values ):
        for val in values:
            if val.reqIDScan():
                searcher = findElemNumInGroup( val.getID().num , headerLst )
                for lid,_ in searcher: val.addPossibleID( lid )
                    
    for dialog in dialogFile._dialogs:
        if dialog.reqIDScan(): _scanNodeList( dialog._values )


def InMemDialog( path, dialogs ):
    """An easy way to get a new file in one line. If you want to just save
    a group of dialogs."""
    f = RCDialogFile( path )
    f._dialogs = dialogs
    return f

class RCDialogFile( LSCSV ):
    """ A Dialog File is essentially a CSV file that is used to house all of
    the dialog information for any MSVS project in such a way as to be able
    to quickly pull out or push back language information (particularly the
    strings). 
    """
    HEADER_ROW   = 0
    CONTROL_COLS = 1
    HEADER_COLS  = ['id'] 
    
    def __init__(self, path):
        ## We are a CSV file but with sections enabled.
        super().__init__(path)
        self.setHasSections() 
        self._dialogs = []
        
    @staticmethod        
    def merge( newpath, firstDialogFile, secondDialogFile, preloaded=True, bypassScan=False ):
        """Merges two dialog files, this may be important during the step to get ALL 
        RCDialogFiles into the translation files.
        """
        import copy 
        totalDialogs = RCDialogFile( newpath )
        if not preloaded:
            firstDialogFile.load()
            secondDialogFile.load()
        ids = [] # to keep track of the dialogs, we still may need to remove more.
        for dialog in firstDialogFile._dialogs:
            ids.append( dialog.id )
            found = False
            for odialog in secondDialogFile._dialogs:
                if dialog.id == odialog.id:
                    totalDialogs._dialogs.append( RCDialog.mergeDialogs(dialog, odialog) )
                    found = True
                    break
            if not found: #FIXME: lOGG MEEE!!
                totalDialogs._dialogs.append( copy.deepcopy( dialog ) )
                
        #now loop through the second dialog and see if there are any dialogs we didn't add.
        for dialog in secondDialogFile._dialogs:
            if dialog.id not in ids: #FIXME: lOGG MEEE!!
                totalDialogs._dialogs.append( copy.deepcopy( dialog ) )
                
        #return our newly made dialog
        return totalDialogs
        
    def update(self, otherDialogFile):
        """Updates this file with the values present in the other, it will NOT
        add new values, and will NOT change the order. It will only add new
        langcodes and adjust already present ones.
        """
        for index in range(len(self._dialogs)):
            for odlog in otherDialogFile._dialogs:
                if self._dialogs[index].id == odlog.id:
                    self._dialogs[index].updateValues( odlog )
                    break
    
    def save(self, newpath=None):
        """Save the current RCDialogFile to its path."""
        if len(self._dialogs) == 0: return False
        if newpath is not None: self._path = newpath
        #create header
        lst = {}
        for e in self._dialogs:
            for l in e.getPossibleLangs(): lst[l]=1
        langorder = list(lst.keys())
        header = RCDialogFile.HEADER_COLS+langorder
        sections = {}
        
        for dialog in self._dialogs:
            ##
            ## The build lines function is what would need to change in the
            ## event of changing the number of columns in the file.
            ##
            sections[dialog.id] = self.__buildLines( dialog, langorder ) 
        writer = self.writeLine(header)
        self.writeSections(sections, writer)
    
    def load(self):
        """Load the dialogs into memory."""
        offset = RCDialogFile.CONTROL_COLS
        header = self.getHeader( RCDialogFile.HEADER_ROW )
        if len(header) < offset: 
            raise Exception("File does not have enough control columns.")
        
        langcodes = len(header)-offset;
        sections = self.readSection(0)
        for name, entries in sections: #For each section make a dialog
            dialog = RCDialog( name )
            #For each entry add it as a string value to the dialog
            for entry in entries: 
                value = RCStringValue(entry[0]) #id
                ####################################
                ## Here is where you would add other control cols
                self.__loadFromLine( entry, dialog )
                ####################################
                # For each langcode column add it to the string value.
                for c in range(langcodes):
                    value.addValuePair(header[offset+c], entry[offset+c])
                dialog._values.append(value)
            self._dialogs.append( dialog )
        return True


    def __loadFromLine(self, line, dialog ):
        ### Add other items we may add in the future to the dialog.
        pass 

    def __buildLines(self, dialog, langorder):
        ### Builds a 2D list of lists that are the entries for saving the 
        ### given dialog.
        if len(langorder) == 0: return []
        lines = []
        for entry in dialog._values:
            line = [entry.getID()]
            for lang in langorder:
                line.append(entry.getValue(lang,''))
            lines.append(line)        
        return lines
        
        
        
        
        