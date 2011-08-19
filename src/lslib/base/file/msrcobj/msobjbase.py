#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
"""The base objects of all internal Microsoft resource objects. These are
used internally in all objects in this directory. They primarily hold 
localizable data mapped to an ID which itself is mapped to an element 
number. 

We use this data in the system to construct/parse/search/push and pull
all of the objects into and out of the primary resource files in any 
given project.
"""
import logging

class RCValueID: 
    """A Value pair of (ID, Element Number). It is used wherever you should
    be able to view/see an element id. Menus, dialogs, string tables. All
    use these.
    """
    def __init__(self, id, num=None):
        self.id = id
        self.num = num
        self.possibleIDs = []
       
    def addPossibleID(self, id):
        """When trying to determine what ID this Value corresponds, its nice
        to keep track of what we've seen already. 
        """
        lst = {}
        for pid in self.possibleIDs:
            lst[pid] = 1
        lst[id] = 1
        self.possibleIDs = list(lst.keys())
        
    def needsHeader(self):
        """A Value ID needs headers when it only has a element Number and
        no ID. This can be a problem when merging.
        """
        return self.id is None and self.num is not None
        
    def asTuple(self): 
        """Generates the RCValueID into a tuple."""
        return self.id, self.num
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        if self.id is None:
            return str(self.num)
        else: return str(self.id)
    
    def __eq__(self, other):
        # Notice we look by ID and never reference the number, as they can
        # be repeated within the same project.
        if type(other) is str:
            return other == str(self.id)
        elif type(other) is tuple: #order = id, num
            return self.asTuple() == other
        elif type(other) is RCValueID:
            return self.id == other.id
        else: return False
        
class RCStringValue:
    """An RC* can have several values that each have their own 
    language code. In other words, every node needs to have an ID 
    mapped to a mapping of language code to value. Thats what the
    RCStringValue is and does for the RC*.
    """
    def __init__(self, newID=None):
        self.__id = None
        self.values = {}
        self.setID( newID ) #update our ID.
        
    def reqIDScan(self):
        """Checks whether the id of this value requires a scan to find."""
        return self.__id.needsHeader()
        
    def setID(self, newID):
        """Set the ID of this string value."""
        if newID is None: 
            self.__id = None
        elif type(newID) is str:
            if type(self.__id) is RCValueID:
                self.__id.id = newID
            else: 
                self.__id = RCValueID( newID )
        elif type(newID) is RCValueID:
            self.__id = newID
        else: raise TypeError("Ids are suppose to be a RCValueID or string.")

    def getID(self):
        """Since IDs are private and strictly monitored we make sure
        only the right people have access with this function.
        """
        return self.__id
        
    def addPossibleID(self, newId):
        """Forward the possible id to the current id for holding. Merger will pick
        this up and validate based on it.
        """
        self.__id.addPossibleID(newId)
        
    def getPossibleIDs(self):
        """Retrieves the possible ids stored in the ID. """
        if self.__id is None: return []
        else: return self.__id.possibleIDs    
        
    def addValuePair(self, langcode, value):
        """Add a language code mapping to a value."""
        if value is not None: 
            self.values[langcode] = value
        else: self.values[langcode] = ''
        
    def getValue(self, langcode, default=None):
        """Get the value of a particular language code."""
        try:    return self.values.get(langcode, default)
        except: return default
    
    def getLangCodes(self):
        """Get all of the possible language codes this value contains."""
        return list(self.values.keys())   
   
    def limitByCodes(self, codes):
        """Returns a new RCStringValue based on the lang-code list given."""
        if codes is None or len(codes) < 1: return self
        newval = RCStringValue(self.__id)
        for lang in codes:
            val = self.getValue(lang)
            if val is not None: newval.addValuePair(lang, val)
        return newval
   
    def combine(self, other, dontMergeLikeKeys=False, suppressIDWarn=False, intelligent=True):
        """Combines two RCStringValue objects into one. When 
        `dontMergeLikeKeys` is True it will skip over language codes that are
        already present in the RCStringValue. Otherwise (as default), it will
        do one of two things: If `intelligent` is False it will erase the old 
        one and replace it with the new one, otherwise it will try to 
        intelligently merge the two values (see below). The `suppressIDWarn` 
        value shouldn't be touched unless you know why the two ids could be 
        merging.
        """
        if type(other) is not RCStringValue:
            raise TypeError("Can only combine two RCStringValue(s)!")
        if not suppressIDWarn and other.getID() != self.getID():
            logging.warning("Combined two RCStringValues of different IDs (%s:%s, %s:%s)."%(self.getID(),self.getPossibleIDs(), other.getID(), other.getPossibleIDs()))
        import copy
        if not intelligent:
            for okeys in other.getLangCodes():
                if dontMergeLikeKeys and okeys in self.values: continue
                self.values[okeys] = copy.deepcopy( other.values[okeys] )
        else:
            # If my current value is the same as another one of my values,
            # then I'm probably not worth saving. Same goes for what is 
            # being pushed in here. (i.e., 
            #   A = {1033:'hi'}
            #   B = {2058:'hola'}
            #   C = {1033:'hi', 2058:'hi'}
            #   D = {1033:'hi',2058:'hola'}
            # Optimistically we would want to be able to merge all of these
            # and still get D. There would be problems if we had two C's 
            # merging, but one of the C's was all in Spanish. We would 
            # have no idea how to solve. But here is the algorithm:
            
            # Merge the two dictionaries such that we have two values for
            # every key at worst. (i.e., vals is of the form {key -> [a,b]})
            vals = {}
            for key,val in self.values.items(): vals[key] = [val]
            for key,val in other.values.items():
                if vals.get( key ) is None: vals[key] = [val]
                elif not dontMergeLikeKeys: vals[key].append(val)
                
            # Remove all items that are alike in the lists. (i.e. [a,a] => [a])
            # We then lock any values that are by themselves.
            newvals = {}
            locked = []
            for key,val in vals.items():
                if len(val) == 2:
                    if val[0] == val[1]: 
                        newvals[key] = [val[0]]
                        locked.append( val[0] )
                    else: newvals[key] = val
                else: 
                    newvals[key] = val
                    locked.append(val[0])
            
            # Then we go through and delete all locked items from 
            # values that have more than one option left.
            res = {}
            broken = [] #list of keys that need to be fixed
            for key, vals in newvals.items():
                newval = ''
                if len(vals) > 1:
                    possibles = []
                    for val in vals:
                        if val not in locked:
                            possibles.append( val )
                    if len(possibles) == 1:
                        newval = possibles[0]
                    else: 
                        broken.append(key)
                        continue
                elif len(vals) == 0:
                    broken.append(key)
                    continue
                else: newval = vals[0]
                res[key]=newval
            
            # Clean up the list of broken language codes, we will just
            # use what we had previously.
            for lang in broken:
                if lang in self.values:
                    res[key] = self.values.get(key,'')   
                    
            #logging.warning("combining vals: self=%s, other=%s, new=%s"%(self.values,other.values, res))  
            self.values = copy.deepcopy(res)
                
    def __repr__(self): #for debugging
        return "(%s, %s)"%(self.__id, self.values)


    def compare(self, other, ignoreID=False, retErr=False):
        if ignoreID or self.__id is None or other.getID() is None:
            #if there is at least one language VALUE that ISNT
            # the exact same, then it can't be the same.
            err = False
            for lang in self.getLangCodes():
                if other.getValue(lang,'') != self.values[lang]:
                    if retErr: return False, err
                    else: return False
                else: err = True
            if retErr: return True,False
            else: return True
        else:
            if retErr: return self.__id == other.getID(), False
            else: return self.__id == other.getID()

    def __eq__(self, other):
        if type(other) is not RCStringValue:
            return False
        else: return self.compare( other )
            