#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""Python has a fairly complete CSV file implementation, however there
are certain features that remain missing that would be helpful for certain
things the LiVSs likes using. Namely sections and whole column selection.

LATER:
   *- CSV sections: groups of data, ie a single line depicting the section and then following rows are within the section.
   *- grabbing sections
   *- grabbing just a column
   *- pretending first column is a key value
   *- returning a set of maps based on first column key value 
    - combining csv files into one or into xlsx file.
    - Updater functions! (update lines that match expression maybe?)
   ?- auto load everything into memory.
 *Finished
 ?Don't know if helpful
"""
import re
import csv

class LSCSV( ):
    """A LiVSs CSV file is a normal CSV with some added features. It can
    group several lines into a 'Section' that has a title. This is so that
    we can group multiple projects or multiple dialogs in the same file 
    without mixing up the values.
    """
    def __init__(self, path):
        self._path = path
        self.__hasSections = None
        
    def setHasSections(self, hasSections=True):
        """A quick way of making all the variables match."""
        self.__hasSections = hasSections
        
    def readLine(self, startRow=0):
        """Read line by line. Not very useful if you don't
        know if the file has sections or not.
        """
        reader = csv.reader( open(self._path, 'r', newline=''), delimiter=',', quotechar='"' )
        count = 0
        try:
            for row in reader: 
                if count >= startRow: yield row
                count+=1
        except csv.Error: pass #explicit catch, remove NULL bytes
        
    def readSection(self, startRow=0):
        """Similar to readLine(), but returns 2D lists of 
        whole sections each time rather than lists.
        """
        lines, name, listen = [], "", False
        for row in self.readLine( startRow ):
            if self.__isHeader( row ):
                if listen: 
                    yield name, lines
                    lines, name = [],""
                else: listen = True
                name = row[0][1:-1]#cutting off delims
                continue
            if listen: lines.append( row )
        if len(lines) > 0: yield name, lines
        
    def writeLine(self, line, writer=None):
        """Writes a line to the excel style csv.
        """
        if type(line) is not list:
            raise TypeError("Can only write a list of elements to the CSV! Not %s!"%type(line))
        if writer is None: writer = csv.writer( open(self._path, 'w', newline=''))
        writer.writerow(line)
        return writer
    
    def writeLines(self, lines, writer=None):
        """Writes Multiple lines to the csv file. Useful 
        for writing whole sections without the needed header.
        """
        if type(lines) is not list:
            raise TypeError("Writelines needs a list of lines!")
        if len(lines) == 1: 
            self.writeLine(lines[0], writer)
        elif len(lines) > 1:
            if writer is None:
                writer = self.writeLine(lines.pop(0))
            writer.writerows( lines )
        return writer
                
    def writeSections(self, sections, writer=None):
        """Writes a section to the csv file. A section is a grouping of
        lines (non-standard csv). The parameter for the section must be
        a map, where the name is the key and the value is a list of lines. 
        """
        if type(sections) is not dict: 
            raise TypeError("WriteSections needs a map to write! Not %s!"%type(sections))
        if writer is None:
            writer = csv.writer( open(self._path, 'w', newline='\n'))
        for name, lines in sections.items():
            self.writeLine(["["+name+"]"], writer)
            self.writeLines(lines, writer)
        return writer
    
    def __isHeader(self, line):
        """The only way for a line to be a header is if it matches
        the regex below.
        """
        tmp = str(line)
        if type(line) is list: tmp = ",".join(line)
        return re.search("^\[.+\]((,)?)*$", tmp) is not None
    
    def getHeader(self, headerRow=0):
        """Pull out the header column by reading out the specified line.
        This could also be used as a "get line". 
        """
        for line in self.readLine( headerRow ): return line
    
    def getColumn( self, colnum, hasSections=False, startRow=0):
        """Gets a whole column as a list. If the column doesn't exist, then a
        Value error is raised. Warning! If the file has sections, then the
        section headers will be pulled out if looking at column 0. Be sure
        to set hasSections to True if you don't want this to happen.
        """
        if colnum < 0: raise IndexError("Invalid Column number")
        try:
            column = []
            if hasSections or self.__hasSections:
                for section in self.readSection( startRow ):
                    for lines in section.values(): # there is only one in the map
                        for line in lines: column.append(line[colnum])
            else:
                for line in self.readLine( startRow ):
                    column.append(line[colnum])
            return column
        except IndexError:
            raise IndexError("Column number given was out of range")
        
    def mapColumns(self, keyColNum, valColNum, hasSections=False, startRow=0):
        """ Grabs two columns and maps them together so that one is the key for the
        other. If valColNum is a list of column numbers, then the value will also be 
        a list of values at that column.  
        """
        vals = []
        if type(valColNum) is list: vals = valColNum
        else: vals.append( valColNum )
        try:
            mapping = {}
            if hasSections or self.__hasSections:
                for section in self.readSection( startRow ):
                    for lines in section.values(): # there is only one in the map
                        for line in lines: 
                            mapping[ line[keyColNum] ] = self.__grabIndexs(vals, line)
            else:
                for line in self.readLine( startRow ):
                    mapping[ line[keyColNum] ] = self.__grabIndexs(vals, line)
            return mapping
        except IndexError:
            raise IndexError("Column number given was out of range!")
        
    def __grabIndexs(self, indexs, lst):
        """Grabs all the index that it needs to from lst."""
        ret = []
        for index in indexs: ret.append(lst[index])
        return ret
    