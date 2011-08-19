#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""A Translation file (aka Excel Workbook file (xls)), is a file that
makes it easy on our translators but is also easy to parse out and transfer
into our MenuFile(s), DialogFile(s), and StrTblFile(s). 

Their format is an Excel Workbook as its able to be opened by almost anyone
on windows, or anyone with OpenOffice.org installed. This made it an ideal
type for distribution and translation. It also has the added ability to have
multiple work-sheets in the same file, which allows us to essentially import
all three file types into their own sheet! This obviously has its benefits.

Excel files however are somewhat difficult to open and parse as they arn't \
well documented [1] and there are little to no open-source (ie, monetarily 
free) libraries for them in any language.

However, we have found a few and chose two that seem to work best for our
purposes. Please consult their documentation for more information [2,3]. If 
there are any changes to its code-base then we'll probably need to update
LiVSs. (However both have had their development halted as of 3/1/2011.)

[1] - http://sc.openoffice.org/excelfileformat.pdf
[2] - http://packages.python.org/xlrd3/
[3] - http://packages.python.org/xlwt3/
"""
import re
import uuid
import copy
import logging

import xlutils.xlwt3 as xlwt #writing excel files
import xlutils.xlrd3 as xlrd #reading excel files

from lslib.util.lcid import ToLanguageString, ToLocalID
from lslib.base.pruning import Pruner

from lslib.base.file.msrcobj.msobjbase     import RCStringValue
from lslib.base.file.msrcobj.dialogex      import RCDialog
from lslib.base.file.msrcobj.stringtable   import RCStrTbl

from lslib.base.file.syslvl.SysMenuFile    import SysMenuFile
from lslib.base.file.syslvl.SysStrTblFile  import SysStrTblFile
from lslib.base.file.syslvl.SysDialogFile  import SysDialogFile
from lslib.base.file.syslvl.SysMenuFileCSV import ConvertMenuXML2CSV, \
                                                  ConvertMenuCSV2XML, \
                                                  SysMenuFileCSV
                                                  

IDMatcher         = re.compile("^(([0-9A-Za-z_\-\.]+),?)+$")#id,id,...
MenuIdMatcher     = re.compile("^m\.(.+?)\.(.+)$")          #m.id.xpath
DialogIdMatcher   = re.compile("^d\.([0-9]+)\.(.+?)\.(.+)$")#d.projkey.dialogid.strid
ConstantIdMatcher = re.compile("^c\.([0-9]+)\.(.+)$")       #c.projkey.constantid

## Excel stylings
HEADER_STYLE = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
NORMAL_STYLE = xlwt.style.default_style
CONFLICT_STYLE = xlwt.easyxf('pattern: pattern solid, fore-colour red')


def MakeTranslationFile( newpath, menu, dialog, strings, preloaded=True, 
                                                         autosave=False, 
                                                         langcodes=None, 
                                                         order=False, 
                                                         trim=True,
                                                         prunepath=None,
                                                         markconflicts=False ):
    """One hit KO method of getting a translation file from system utility
    files. If you set `preloaded` to False, then it will re-load the three
    utility files, otherwise it will assume they've been loaded into memory.
    Setting `autosave` to True will make this function save the translation 
    file before returning it.
    """
    if type(menu) is not SysMenuFile or \
       type(dialog) is not SysDialogFile or \
       type(strings) is not SysStrTblFile:
        raise TypeError("One or more of the files given were not correct system files!")
    
    if not preloaded: menu.load() ; dialog.load() ; strings.load()
    
    prime = None if langcodes is None or len(langcodes)==0 else langcodes[0]
    trans = TranslationFile( newpath, prime, prunepath, markconflicts )
    csvmenu = ConvertMenuXML2CSV( 'tmp.cm', menu )
    trans.setSysFiles( csvmenu, dialog, strings )
    
    if autosave: trans.save(langcodes=langcodes, order=order, trim=trim)
    return trans


class TranslationFile(): 
    """A Translation File is an Excel Workbook with two work-sheets. The
    first worksheet is for Menus, Dialogs, and StringTables all merged together 
    and the second is utility information to be ignored by the translators 
    (there will be a message that says so). The main worksheet is a condensed 
    form of its parent utility files to save on translation costs. This means 
    that there will only be unique strings for each line.
    
    On the first worksheet, the first column is a utility column that should 
    be ignored by the translators, it will be minimized and/or hidden to 
    reduce clutter. The first column is a list of strings for translation, and
    they should just fill in the column next to it. 
    """
    SHEET_NAMES = { 0:"Strings",
                    1:"util" }
    STRINGS_SHEET = SHEET_NAMES[0]
    UTIL_SHEET    = SHEET_NAMES[1]
    HEADER_COLS = ['id']
    UTIL_SHEET_WARNING = \
    """***DO NOT EDIT! THIS IS USED FOR PARSING THIS TRANSLATION FILE AFTERWARD.***"""
    
    def __init__(self, path, primaryLangCode, prunepath=None, markconflicts=False):
        """Create a translation file at the specified path. If `mergeKey` is 
        not None, then the Translation file will do its comparisons based on
        the language code (LCID) given; examples are '1033' or '2058'. This 
        means it will compare and combine on that language code. So if '1033' 
        was given all similar '1033' values for ALL STRINGS IN THE SYSTEM will
        be pushed into one line.
        """
        self.__path = path
        self.__primaryLangCode = primaryLangCode
        self.__markconflicts = markconflicts
        self.__mergelist = {} #mid -> [id]
        self.__strings = {} # mid -> RCStringValue => sheet1
        self.__conflicts=[] # [mid]                => sheet1 (if markConflicts is True)
        self.__utils   = {} # idn -> (order,type)  => sheet2
        self.__projs   = {} # projname -> number   => sheet2
        self.__seps    = [] # [ xpath-id ]         => sheet2
        self.__pruned  = {} # mid -> RCStringValue => sheet2
        self.__pruner  = Pruner( prunepath )
        
    def getPath(self):
        """Gets the path of the Translation File."""
        return self.__path
    
    def load(self, newpath=None):
        """Loads the translation file into memory for use. If `newpath` is
        set, then the file is changed.
        """
        if newpath is not None: self.__path = newpath
        # Load the utils first:
        self.__loadUtilLines()
        # Then load the strings:
        self.__loadStringLines()
        return True
            
    def save(self, langcodes=None, order=False, newpath=None, trim=False):
        """Saves the Translation file to the specified path, or the path
        given to it upon instantiation.
        """
        if newpath is not None: self.__path = newpath
        workbook = xlwt.Workbook()
        
        strings = workbook.add_sheet( self.STRINGS_SHEET )
        util    = workbook.add_sheet( self.UTIL_SHEET )        
        langcodes = self._makeLangList() if langcodes is None else langcodes
        head      = self._makeHeader(langcodes)
        
        lines, conflicts = self.__getStrLines( langcodes, order, trim )
        self.__writeLines( strings, 
                           lines, 
                           header=head,
                           conflictIndexs=conflicts,
                           headermagic=True)
        self.__writeLines( util, 
                           self.__getUtilLines(head, langcodes, order, trim), 
                           header=[self.UTIL_SHEET_WARNING],
                           hideUtilCol=False)
        
        workbook.save(self.__path)


    def getSysMenuFile(self, path, save=False, langcodes=None):
        """ Generates a System Menu File from the internals of the translation
        file. This does not save the file, instead is merely returned. This can
        be changed, by setting `save` to True.
        """
        csvfile = self.getSysMenuFileCSV('tmp.cmenus', langcodes=langcodes)
        return ConvertMenuCSV2XML(path, csvfile, autosave=save)
    
    def getSysMenuFileCSV(self, path, save=False, langcodes=None):
        """Generates a System Menu CSV File from the internals of the translation 
        file. This does not save the file, instead is merely returned. This can
        be changed, by setting `save` to True.
        """
        global MenuIdMatcher
        csvfile = SysMenuFileCSV(path)
        data ={}
        for mid, ids in self.__mergelist.items():
            for idn in ids:
                if MenuIdMatcher.search(idn) is not None:
                    newid = idn.split(".",1)[1]
                    try:    data[newid] = self.__strings[mid].limitByCodes(langcodes)
                    except: data[newid] = self.__pruned[mid].limitByCodes(langcodes)
        csvfile._setInternals(data, self.__projs, self.__utils, self.__seps)
        if save: csvfile.save()
        return csvfile
    
    def getSysDialogFile(self, path, save=False, langcodes=None):
        """ Generates a System Dialog File from the internals of the 
        translation file. This does not save the file, instead is merely 
        returned. This can be changed, by setting `save` to True.
        """
        global DialogIdMatcher
        dlog = SysDialogFile(path)
        projdialogs = {} # projkey -> { dialogid -> dialog }
        for mid, ids in self.__mergelist.items():
            for idn in ids:
                if DialogIdMatcher.search(idn) is not None:
                    projkey, did, strid = DialogIdMatcher.search(idn).groups()
                    try:    val = copy.deepcopy( self.__strings[mid] )
                    except: val = copy.deepcopy( self.__pruned[mid] )
                    val.setID( strid )
                    val = val.limitByCodes( langcodes )
                    
                    if projdialogs.get(projkey) is None:
                        projdialogs[projkey] = {}
                    
                    if projdialogs[projkey].get(did, None) is None:
                        dialog = RCDialog(did)
                        dialog._values.append(val)
                        projdialogs[projkey][did] = dialog
                    else:
                        projdialogs[projkey][did]._values.append(val)
        
        for projkey, dlogs in projdialogs.items():
            dlog._projs[self.getProjName(projkey)] = dlogs.values()
        if save: dlog.save()
        return dlog
    
    def getSysStrTblFile(self, path, save=False, langcodes=None):
        """ Generates a System String Table File from the internals of the 
        translation file. This does not save the file, instead is merely 
        returned. This can be changed, by setting `save` to True.
        """
        strtblfile = SysStrTblFile( path )
        projtables = {} # projkey -> RCStrTbl
        for mid, ids in self.__mergelist.items():
            for idn in ids:
                if ConstantIdMatcher.search(idn) is not None:
                    projkey, consid = ConstantIdMatcher.search(idn).groups()
                    try:    val = copy.deepcopy( self.__strings[mid] )
                    except: val = copy.deepcopy( self.__pruned[mid] )
                    val.setID( consid )
                    if projtables.get(projkey, None) is None:
                        projtables[projkey] = RCStrTbl()
                    projtables[projkey].addStringValue( val.limitByCodes(langcodes) )
        for proj, strtbl in projtables.items():
            strtblfile._projs[ self.getProjName(proj) ] = strtbl
        if save: strtblfile.save()
        return strtblfile

    
    def updateWithMenuFile(self, menuFile, preloaded=True, saveAfter=False):
        """Updates the translation file with the values of a system level
        menu file. It will not save the translation file unless `saveAfter` is
        True. The `preloaded` parameter is to know whether the file has been 
        loaded into memory already.
        """
        csvmenu = ConvertMenuXML2CSV('tmp.cmenus', menuFile, preloaded)
        dialogs = self.getSysDialogFile('tmp.dialogs')
        strings = self.getSysStrTblFile('tmp.strtbls')
        self.setSysFiles(csvmenu, dialogs, strings)
        if saveAfter: self.save()
    
    def updateWithDialogFile(self, dialogFile, preloaded=True, saveAfter=False):
        """Updates the translation file with the values of a system level
        dialog file. It will not save the translation file unless `saveAfter`
        is True. The `preloaded` parameter is to know whether the file has been 
        loaded into memory already.
        """
        if not preloaded: dialogFile.load()
        csvmenu = self.getSysMenuFileCSV('tmp.cmenus')
        strings = self.getSysStrTblFile('tmp.strtbls')
        self.setSysFiles(csvmenu, dialogFile, strings)
        if saveAfter: self.save()
    
    def updateWithStrTblFile(self, strFile, preloaded=True, saveAfter=False):
        """Updates the translation file with the values of a system level
        string table file. It will not save the translation file unless 
        `saveAfter` is True. The `preloaded` parameter is to know whether the 
        file has been loaded into memory already.
        """
        if not preloaded: strFile.load()
        csvmenu = self.getSysMenuFileCSV('tmp.cmenus')
        dialogs = self.getSysDialogFile('tmp.dialogs')
        self.setSysFiles(csvmenu, dialogs, strFile)
        if saveAfter: self.save()
      
      
    def setSysFiles(self, csvmenu, dialogs, strings):
        """Adds the three files. Assume that this function will overwrite ALL
        current data. It will not do any updating.
        """
        self.__strings, self.__utils, self.__projs, self.__seps, self.__pruned = {}, {}, {}, [], {}
        self.__projs, self.__utils, self.__seps = csvmenu._getXMLUtilSections()
        data = csvmenu._getXMLDataSection()
        for id, val in data.items(): #the csv makes it easy
            newid = "m.%s"%id
            self.__addStringLine(newid, val)   
        
        for project, table in strings._projs.items():
            try:
                if table is None: continue
                for val in table._values:
                    newid = "c.%d.%s"%(self.getProjKey(project), str(val.getID()))
                    self.__addStringLine(newid, val)
            except KeyError:
                logging.error("Project %s doesn't exist in given string table file."%project)
        
        for project, dlogs in dialogs._projs.items():
            try:
                for dlog in dlogs:
                    newid = "d.%d.%s"%( self.getProjKey(project), str(dlog.id))
                    for val in dlog._values:
                        vid = "%s.%s"%( newid, str(val.getID()))
                        self.__addStringLine(vid, val)
            except KeyError:
                logging.error("Project %s doesn't exist in given dialog file."%project)
        
    def getProjKey(self, name):
        """Get the project number mapping for a project name."""
        try:
            return self.__projs[name]
        except:
            maxval = max(self.__projs.values())
            self.__projs[name] = maxval+1
            return maxval+1
            
    
    def getProjName(self, num):
        #logging.error("num = %s, projs= %s"% (num, self.__projs))
        for k,v in self.__projs.items():
            #logging.error("getting projname: %s ?= %s"%(v,num))
            if v == num: return k
        raise Exception("Couldnt find name!!")
    
    
    def getProjNames(self):
        """ Returns a list of all the projects in the translation file."""
        return list(self.__projs.keys())
    
    
    def _makeLangList(self):
        lst = {}
        for val in self.__strings.values():
            for l in val.getLangCodes(): lst[l]=1
        langorder = list(lst.keys())
        return langorder
        
    def _makeHeader(self, langcodes):
        langs = []
        for langcode in langcodes:
            lang= ToLanguageString( int(langcode) )
            if lang is None: langs.append(langcode)
            else: langs.append( lang )
        return TranslationFile.HEADER_COLS+langs
        
    def __addStringLine(self, idn, value):
        found = False
        if not self.__pruner.isPrunable( value, self.__primaryLangCode ): #then add to strings dict
            err = False
            for mid, val in self.__strings.items():
                comp,err = val.compare( value, ignoreID=True, retErr=True )
                if err and self.__markconflicts: 
                    self.__conflicts.append(mid) 
                if comp:
                    self.__mergelist[mid].append(idn)
                    self.__strings[mid].combine(value, True,True)
                    found = True
                    break
            if not found:
                mid = uuid.uuid4()
                self.__mergelist[mid] = [idn]
                if err and self.__markconflicts: 
                    self.__conflicts.append(mid)
                self.__strings[mid] = value
        else: #since we can prune it, lets add it to the prune list.
            for mid, val in self.__pruned.items():
                if val.compare( value, ignoreID=True ) :
                    self.__mergelist[mid].append(idn)
                    self.__pruned[mid].combine(value, True,True)
                    found = True
                    break
            if not found:
                mid = uuid.uuid4()
                self.__mergelist[mid] = [idn]
                self.__pruned[mid] = value
        
    def __translateCodes(self, langstrs):
        codes = []
        for langstr in langstrs:
            code = ToLocalID(langstr)
            if code is None: 
                logging.error("COULD NOT DETERMINE LOCAL ID FROM: %s"%langstr)
                code = ''
            codes.append(str(code))
        return codes
        
    def __loadStringLines(self):
        global IDMatcher
        rows = self.__readSheet( TranslationFile.STRINGS_SHEET, 0 )
        langcodes = []
        headeroffset = len(TranslationFile.HEADER_COLS)
        for head in rows:
            langcodes = head[headeroffset:]
            break
        langcodes = self.__translateCodes( langcodes )
        for row in rows:
            midlist=row[0].split(",")
            col = 1
            val = RCStringValue()
            for lang in langcodes:
                val.addValuePair(lang, row[col])
                col+=1
            #add value 
            for idn in midlist: self.__addStringLine(idn, val) #OMG SO SLOW, but it works
    
    def __loadUtilLines(self):
        rows = self.__readSheet( TranslationFile.UTIL_SHEET, 1 )
        langcodes = []
        headeroffset = len(TranslationFile.HEADER_COLS)
        for head in rows:
            langcodes = head[headeroffset:]
            break
        langcodes = self.__translateCodes( langcodes )
        projOrUtil = 0 # 0=proj,1=util,2=seps,3=pruned
        
        for row in rows: 
            if row[0] == "PROJMAP":
                projOrUtil = 0
                continue
            elif row[0] == "XMLUTIL":
                projOrUtil = 1
                continue
            elif row[0] == "SEPS":
                projOrUtil = 2
                continue
            elif row[0] == "PRUNED":
                projOrUtil = 3
                continue
            elif IDMatcher.search(row[0]) is not None:
                if projOrUtil==1 and row[1].isdigit():
                    idn, order, typeid, *_ = row #ignore the man behind the curtain
                    self.__utils[idn] = (order, typeid)
                elif projOrUtil==2:
                    self.__seps.append( row[0] )
                elif projOrUtil==3:
                    midlist=row[0].split(",")
                    col = 1
                    val = RCStringValue()
                    for lang in langcodes:
                        val.addValuePair(lang, row[col])
                        col+=1
                    mid = uuid.uuid4()
                    self.__mergelist[mid]=midlist
                    self.__pruned[mid]=val
                else:
                    #sometimes a project name might match an ID, in 
                    # these instances we have to be careful.
                    if projOrUtil==0 and row[1].isdigit() and self.__rest(2, row, ''):
                        self.__projs[ row[0] ] = row[1]
                    else:
                        logging.debug("UNKNOWN UTIL LINE: %s, state=(%d)"%(row, projOrUtil))
                        continue #broken line?
            else:
                if projOrUtil==0 and row[1].isdigit():
                    self.__projs[ row[0] ] = row[1]
                else: 
                    logging.debug("UNKNOWN UTIL LINE: %s"%row)
                    continue #broken line?
      
    def __rest(self, strtIndex, row, val):
        for x in range(strtIndex, len(row)):
            if row[x] != val: return False
        return True
    
    def __breakUpList(self, lst, maxsize=30000, fakeLimit=300, newlst=None):
        if len(",".join(lst)) > maxsize:
            size = int(len(lst)/2)
            #break the list into equal parts
            a,b = lst[:size], lst[size:]
            #recurse on each part
            alst = self.__breakUpList(a,newlst=newlst)
            blst = self.__breakUpList(b,newlst=newlst)
            #upon return, concat the two lists and return
            return alst+blst
        else:
            if newlst is None: return [",".join(lst)]
            else:
                newlst.append([",".join(lst)])
                return newlst
    
    def __getUtilLines(self, header, langorder, order=False, trim=False):
        lines = [header]
        lines.append(['PROJMAP'])
        for proj,num in self.__projs.items():
            lines.append([proj, str(num)])
        lines.append(['XMLUTIL'])
        for idn, val in self.__utils.items():
            order, typeid = val
            lines.append([idn, order, typeid])
        lines.append(["SEPS"])
        for xpath in self.__seps:
            lines.append([xpath])
        lines.append(["PRUNED"])
        key = None if not order else (lambda x: x[1].getValue(langorder[0],''))
        for mid, val in sorted(self.__pruned.items(), key=key):
            midlist = ",".join(self.__mergelist[mid])
            if len(midlist) > 30000: #max cell size
                midlines = self.__breakUpList(self.__mergelist[mid])
                for line in midlines:
                    for lang in langorder: 
                        line.append(val.getValue(lang,''))
                    if trim and self.__rest(1, line, ''): continue
                    lines.append(line)
            else:
                line = [midlist]
                for lang in langorder: 
                    line.append(val.getValue(lang,''))
                if trim and self.__rest(1, line, ''): continue
                lines.append(line)
        return lines
    
    def __getStrLines(self, langorder, order=False, trim=False):
        lines = []
        conflictIndexs = []
        remove = len(langorder) <= 1
        key = None if not order or len(langorder)==0 else (lambda x: x[1].getValue(langorder[0], ''))
        for mid, val in sorted(self.__strings.items(), key=key):
            midlist = ",".join(self.__mergelist[mid])
            if len(midlist) > 30000: #max cell size
                midlines = self.__breakUpList(self.__mergelist[mid])
                for line in midlines:
                    for lang in langorder: 
                        tmp = val.getValue(lang,'')
                        if remove and tmp == '': continue 
                        line.append(tmp)
                    if trim and self.__rest(1, line, ''): continue
                    if self.__markconflicts and mid in self.__conflicts:
                        conflictIndexs.append(len(lines))
                    lines.append(line)
            else:    
                line = [midlist]
                for lang in langorder:
                    tmp = val.getValue(lang,'')
                    if remove and tmp == '': continue 
                    line.append(tmp)
                if trim and self.__rest(1, line, ''): continue
            
                if self.__markconflicts and mid in self.__conflicts:
                    conflictIndexs.append(len(lines))
                    
                lines.append(line)
        logging.debug("Unique Strings:%d, Possible Conflicts:%d"%(len(lines),len(conflictIndexs)))
        return lines, conflictIndexs
      
    def __readSheet(self, name, rowstart=0):
        """Reads through a sheet, row by row. Starting at the specified row.
        The return will be a list of strings, similarly to the CSV package. 
        """
        workbook = xlrd.open_workbook(filename=self.__path, on_demand=True)
        sheet = workbook.sheet_by_name(name)
        for rownum in range(rowstart, sheet.nrows):
            vals=[]
            for cell in sheet.row(rownum):
                if cell.ctype in [0,6]: #blank string
                    vals.append('')
                elif cell.ctype == 2: #number
                    try: 
                        val = float(cell.value)
                        vals.append(str(int(val)))
                    except:  vals.append(str(cell.ctype))
                else: #text,date,bool,error
                    vals.append(str(cell.value))
            yield vals
   
    def __writeLines(self, worksheet, lines, header=None, headermagic=False, hideUtilCol=True, conflictIndexs=None):
        global CONFLICT_STYLE, NORMAL_STYLE, HEADER_STYLE
        
        badex = [] if conflictIndexs is None else conflictIndexs
        
        if header is not None:
            col = 0
            format = HEADER_STYLE if headermagic else NORMAL_STYLE
            for val in header:
                worksheet.write(0,col,val,format)
                col+=1
            if headermagic:
                worksheet.set_panes_frozen(True)  # frozen headings instead of split panes
                worksheet.set_horz_split_pos(1)   # in general, freeze after last heading row
                worksheet.set_remove_splits(True) # if user does unfreeze, don't leave a split there
            
        row = 0 if header is None else 1
        curindex = 0
        for line in lines:
            if curindex in badex:
                format = CONFLICT_STYLE
            else: format = NORMAL_STYLE
            col = 0
            for val in line:
                worksheet.write(row, col, val, format)
                col+=1
            row+=1
            curindex+=1
            
        if hideUtilCol: worksheet.col(0).width = 0x0


        