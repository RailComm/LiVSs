#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""Translations cost quite a bit of money per word, so in order to cut down
we can do some pruning to make sure we only get the lines we NEED to maintain.

LiVSs automatically prunes out lines that have now actual characters that are
translatable (e.g. whitespace buffers, numbers, pure formatting strings, etc.
"""
import re
import fileinput

class Pruner:
    def __init__(self, prunepath=None):
        self.__prunelist = []
        if prunepath is not None:
            file = fileinput.FileInput(prunepath, mode='r')
            for line in file:
                self.__prunelist.append(line.splitlines()[0])
            file.close()
            import logging
            logging.debug("prunelist: %s"%self.__prunelist)
        
        
    def isPrunable(self, value, primary=None, only=None):
        """Checks if an RCStringValue is a candidate for pruning."""
        if primary is not None:
            # we only check the primary language to see
            # if its listed.
            prime = value.getValue(primary, '')
            if self.isListed( prime ):
                return True    
            elif self.__isprunable([prime]):
                return True
            else: return False
        else:
            strs = []
            if only is not None:
                for val in only:
                    strs.append( value.getValue(val, ''))
            else: strs = list(value.values.values()) #lolwat?
            
            return self.__isprunable(strs)
            
            
    def __isprunable(self, strs):
        global STATIC_CHECKS
        
        fails = 0
        for s in strs:
            try:
                for check in STATIC_CHECKS:
                    if check( s ):
                        fails+=1
                        break
            except: continue
        #if all strings are prunable then its prunable
        return fails == len(strs)
              
    def isListed(self, s ):
        for regex in self.__prunelist:
            if re.search( regex, s ) is not None:
                return True
        return False

def isDigit( s ):
    return s.isdigit()
def isWhitespace( s ):
    return len(s.strip())==0
def isJustSymbol( s ):
    return re.search("^[,\.:;><_\-\"'\?%]+$", s.strip()) is not None
def isNumTag( s ):
    return re.search("^\s*[0-9]+[a-z]?\.\s*$", s) is not None
def isSingleChar( s ):
    return re.search("^.$", s.strip()) is not None
def isPercentage( s ):
    return re.search("^[0-9]+%$", s.strip()) is not None
def isFloat( s ):
    try:
        float(s)
        return True
    except ValueError:
        return False
def isPureFormatting( s ):
    formater="^((%([A-Za-z]{1,4}|[0-9]+))|[\s,\.\/\-:;><_\"'])+$"
    return re.search(formater,s) is not None  
def isRTFString( s ):
    # This is horrible. But it has to be done like this to avoid
    # problems with regex and escaping characters. Apparently Python3
    # has issues with unicode/raw/ascii encodings and regex escape
    # strings. Otherwise Python2.* can handle an regex of: '^\{+\\+rtf'
    starts = ["{\rtf","{\\rtf","{\\\rtf","{\\\\rtf",
              "{{\rtf","{{\\rtf","{{\\\rtf","{{\\\\rtf",
              "{{{\rtf","{{{\\rtf","{{{\\\rtf","{{{\\\\rtf"]
    for start in starts:
        if s.startswith(start): return True
    return False

STATIC_CHECKS = \
    [
     isDigit,
     isWhitespace,
     isNumTag,
     isFloat,
     isJustSymbol,
     isPercentage,
     isSingleChar,
     isPureFormatting,
     isRTFString
    ]