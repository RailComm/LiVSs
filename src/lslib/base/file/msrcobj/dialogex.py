#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""A dialog is a popup that is displayed through the course of an applications
runtime. This object will hold all data that is tied to a single dialog from a
resource file. Here is an example dialog in a resource file:

IDD_COMMENTDLG DIALOGEX 0, 0, 247, 99
STYLE DS_SETFONT | DS_MODALFRAME | DS_FIXEDSYS | WS_POPUP | WS_CAPTION
CAPTION "Enter Comment"
FONT 8, "MS Shell Dlg", 0, 0, 0x0
BEGIN
    DEFPUSHBUTTON   "OK",IDOK,73,76,50,16
    PUSHBUTTON      "Cancel",IDCANCEL,129,76,50,16
    EDITTEXT        IDC_COMMENT_EDIT,7,7,233,64,ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN | WS_VSCROLL
END

To see how this gets parsed out into this object. See the DialogFile.py in 
lslib.base.file.utility.
"""

class RCDialog: 
    """The RCDialog is the object stored in memory that represents a single
    dialog within one or more resource files (eg, one or more languages).
    
    There is a lot missing currently from this object. It was created for the
    sole purpose to transfer/translate strings. Information regarding placement
    and size of controls are not kept/maintained. Go check out the RCDialogFile
    object, it has more information on how to fit all of this other stuff.
    """
    def __init__(self, id):
        self.id = id
        self._values = []
        self.__static_count = 0
        
    @staticmethod
    def mergeDialogs(first, second, bypassScan=False):
        """Merge two dialogs. They need to be of the same dialog or else this
        is a worthless function. It will check IDs to make sure. If there is 
        a problem merging it will raise an Exception. 
        """
        if type(first) is not RCDialog or \
           type(second) is not RCDialog:
            raise TypeError("Merging dialogs needs two dialogs.")
        
        if first.id != second.id:
            raise AttributeError("Merging dialogs needs two dialogs of the same ID.")
        
        if not bypassScan and (first.reqIDScan() or second.reqIDScan()):
            raise AttributeError("Cannot merge until one or both dialogs get an ID scan.")
        import copy
        newDialog = RCDialog(first.id)
        for val in first._values:
            newDialog.addValue( copy.deepcopy(val), merge=True, checkPossibles=bypassScan )
        for val in second._values:
            newDialog.addValue( copy.deepcopy(val), merge=True, checkPossibles=bypassScan )
        return newDialog
    
    def addValue(self, value, merge=True, overwriteLangCode=False, checkPossibles=False, static=False):
        """Adds a value to the dialog. If the value already exists, then merge 
        the value with the other value already present. If overwriteLangCode 
        is True and both value and the already present value have the same lang
        code, then the old value is over-written. 
        """
        import copy
        if static:#staticize the value. (we found an id == IDC_STATIC)
            val = copy.deepcopy(value)
            val.setID("%s.%d"%(str(val.getID()), self.__static_count))
            self.__static_count+=1
            self._values.append( val )
        elif self.getValue(value.getID()) is None:
            self._values.append( copy.deepcopy(value) )
        elif merge:
            for val in self._values:
                if val.getID() == value.getID():  
                    val.combine( copy.deepcopy(value), overwriteLangCode )
                    break 
                elif checkPossibles and (value.getID() in val.getPossibleIDs()):
                    val.combine( copy.deepcopy(value), overwriteLangCode )
                    break 
                
    def updateValues(self, otherDialog):
        """Update all values with the values in the other dialog. This means 
        that NO NEW VALUES ARE ADDED, it just overwrites the values in the
        current dialog with the values in the other. It also allows for adding 
        new language codes for each particular value.
        """
        for index in range(len(self._values)):
            for oval in otherDialog._values:
                if self._values[index].getID() == oval.getID():
                    self._values[index].combine( oval, intelligent=False )
                    break
        
    def getValue(self, id, langcode='1033', default=None):
        """Gets the value of a given ID found in the dialog.
        """
        for val in self._values:
            if val.getID() == id:
                return val.getValue(langcode, default)
        return default
    
    def getPossibleLangs(self):
        """Used when deriving the headers for a RCDialogFile.
        """
        lst = {}
        for e in self._values:
            for lang in e.getLangCodes():
                lst[ lang ] = 1
        return lst.keys()
        
        
    def reqIDScan(self):
        """Checks whether there are values in the dialog that do not have an ID
        associated with them.
        """
        for val in self._values:
            if val.reqIDScan(): return True
        return False