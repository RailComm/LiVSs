#!/usr/bin/env python3.2
# -*- coding: Latin-1 -*-
#
# Author: Alexander Dean <dstar@csh.rit.edu>
# Copyright (c) 2011, RailComm LLC
# All rights reserved. Redistribution and use in source and binary forms, with 
# or without modification are permitted provided that the conditions are met 
# under the Modified BSD License.
#
__usage__       ="%(prog)s <subcommand> [options] [args [args ...]]"
__version__     ="0.5.0"
__description__ ="""LiVSs is a script for collecting and manipulating 
Visual Studio project resource files. It is meant as an aid in L10n and i18n 
of your own projects as well as making complete data-set backups of all of it
as well. You can even parse your own source code for key bits of information.
"""

#The format of the logging to the screen, log file.
_LOGGING_FORMAT_ = "%(levelname)-8s::[%(asctime)s]-%(funcName)s@%(lineno)d %(message)s"
_DATE_FORMAT_ = "%a, %d %b %Y %H:%M:%S"

import logging
import argparse

from lslib.util.argstr   import * #@UnusedWildImport
from lslib.base.lsrunner import LSRunner
from lslib.base.file.utility.lsscript import LSScript


def setup_argparse():
    """Returns the argument parser that headshot uses."""
    prsr = argparse.ArgumentParser( description=__description__,
                                    version=__version__ )
    subprsrs = prsr.add_subparsers(dest='subparser_name')
    
    sub_export = subprsrs.add_parser(prsr_EXPORT,description=prsr_EXPORT_desc,
                                                help=prsr_EXPORT_help)
    sub_update  = subprsrs.add_parser(prsr_UPDATE, description=prsr_UPDATE_desc,
                                                help=prsr_UPDATE_help)
    sub_script= subprsrs.add_parser(prsr_SCRIPT,description=prsr_SCRIPT_desc,
                                                help=prsr_SCRIPT_help) 
    
    # toplevel options 
    #  --debug     turn on debug logging.
    #  --warnings  let warnings be logged too, errors are the only thing logged by default.
    #  --logfile   set the path to the log file.
    prsr.add_argument('--debug', action='store_true',help="Turn on debug logging.",dest='log_debug')
    prsr.add_argument('--warnings',action='store_true',help="Let warnings be logged too, errors are the only thing logged by default.",dest='log_warnings')
    prsr.add_argument('--logfile', default="errors.log",help="Set the path to the log file.",dest='log_path')
    prsr.add_argument('--save', metavar="path",help="Set the path to where the current query can be saved.",dest='script_save_path')
    prsr.add_argument('--time', action='store_true',help="LiVSs will report how long it took to run your command.",dest='run_timer')
    
    #export subcommand
    # input    the file/directory that should be the target of an export
    # output   the file/directory that should be the location of said export
    #
    # Subcommands of Export
    #   util           options for dumping utility files from the input target
    #   translator     options for dumping a translator file from the input target
    #
    esubprsrs = sub_export.add_subparsers(dest='subsubparser_name')
    util_sub_parse  = esubprsrs.add_parser(subprsr_UTIL, description=subprsr_UTIL_desc, 
                                                        help=subprsr_UTIL_help)
    translator_sub_parse = esubprsrs.add_parser(subprsr_TRANSLATOR,description=subprsr_TRANSLATOR_desc,
                                                        help=subprsr_TRANSLATOR_help)
    sub_export.add_argument('-l','--level', choices=['sys','proj','lang'], help="set the level to build the export to, read the HOWTO if you don't know.",dest='export_level')
    sub_export.add_argument('--mem', action='store_true', help="Keep everything in memory and only saves the level specified, generates new files.",dest='export_mem')
    sub_export.add_argument('--keep', action='store_true', help="Use what was currently generated in the input path, don't generate new files.",dest='export_existing')
    sub_export.add_argument('input', help='the file/directory that should be the target of an export')
    sub_export.add_argument('output', help='the file/directory that should be the location of said export')
    
    # export util subcommand
    #    -m, --menus    export the menus out of the target
    #    -d, --dialogs  export the dialogs out of a target
    #    -s, --strings  export the string tables out of a target
    #    -a, --all      export all utils from a target (output must be a directory)
    util_sub_parse.add_argument('-m','--menus', action='store_true', help='export the menus out of the target',dest='export_util_menus')
    util_sub_parse.add_argument('-d','--dialogs', action='store_true', help='export the dialogs out of a target',dest='export_util_dialogs')
    util_sub_parse.add_argument('-s','--strings', action='store_true', help='export the string tables out of a target',dest='export_util_strings')
    util_sub_parse.add_argument('-a','--all', action='store_true', help='export all utils from a target (output must be a directory)',dest='export_util_all')
    
    # export translator subcommand
    #    -s, --sort       Sort the list of strings alphabetically
    #    -c, --langcodes  Provide a list of language codes you want in the translator file
    #    -p, --prune      Takes a path to a file that has a list of strings that shouldn't be in the translation file
    translator_sub_parse.add_argument('-s','--sort', action='store_true', help="Sort the list of strings alphabetically", dest='export_translator_order')
    translator_sub_parse.add_argument('-c','--langcodes', metavar='code', nargs='+', help="Provide a list of language codes you want in the translator file",dest='export_translator_langcodes')
    translator_sub_parse.add_argument('-p','--prune', metavar='path', nargs=1, help="Takes a path to a file that has a list of strings that shouldn't be in the translation file",dest='export_translator_prunepath')
    translator_sub_parse.add_argument('-m','--mark', action='store_true', help="Highlights possible conflicts in the new translation file", dest='export_translator_markconflicts')

    #update subcommand
    # -t, --translator   Location of input translator file
    # -d, --dialogs      Location of input dialogs file
    # -m, --menus        Location of input menus file
    # -s, --strings      Location of input string table file
    # -c, --langcode     Limit what lang code in the input file gets updated, this can be a list.
    # -o, --outtype      What should we be updating? (sys, proj, rcs)
    # -n, --new          Generates new files for whatever outtype is set to (cannot be rcs).
    # output             The directory/file to update
    locations = sub_update.add_mutually_exclusive_group(required=True)
    locations.add_argument('-t','--translator',metavar='path',help='Location of input translator file',dest='update_translator')
    locations.add_argument('-d','--dialogs',metavar='path',help='Location of input dialogs file',dest='update_dialogs')
    locations.add_argument('-m','--menus',metavar='path',help='Location of input menus file',dest='update_menus')
    locations.add_argument('-s','--strings',metavar='path',help='Location of input string table file',dest='update_strings')
    sub_update.add_argument('-c','--langcode', metavar='code', nargs='+', help="Limit what lang code in the input file gets updated, this can be a list.", dest='update_langcodes')
    sub_update.add_argument('-o','--outtype', metavar='type', choices=['sys','proj','rcs'], help='What should we be updating?', dest='update_to')
    sub_update.add_argument('-n','--new',action='store_true', help='Generates new files for whatever outtype is set to (cannot be rcs).', dest='update_new')
    sub_update.add_argument('output',help='The directory/file to update')
    
    #script subcommand
    # --dump   instead of reading in a file, all default configurations are dumped to the given file
    # path     takes a path to a file to run it. For more information on scripting, see the howto file.
    sub_script.add_argument("--dump", action="store_true", help="instead of reading in a file, all default configurations are dumped to the given file")
    sub_script.add_argument("input", help="takes a path to a headshot script to run it.")
    
    return prsr

    
def setup_logging( cfg ):
    """Sets up the logging based on the read in configuration."""
    global _LOGGING_FORMAT_, _DATE_FORMAT_
    format,date = _LOGGING_FORMAT_,_DATE_FORMAT_
    
    if not cfg.get('logging', True):
        logging.basicConfig(handler=logging.NullHandler)
        return
    
    #check passed in cfgs if formats changed
    if cfg.get('log_format', False):
        format = cfg.get('log_format')
    if cfg.get('log_date_format',False):
        date = cfg.get('log_date_format')
    
    if cfg.get('log_debug', False):
        logging.basicConfig(level=logging.DEBUG,
                            format=format,
                            datefmt=date,
                            filename=cfg.get('log_path', 'errors.log'))
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(console)
        
    elif cfg.get('log_warnings', False):
        logging.basicConfig(level=logging.WARNING,
                            format=format,
                            datefmt=date,
                            filename=cfg.get('log_path','errors.log'))
        
    else:# Errors are always logged. deal.
        logging.basicConfig(level=logging.ERROR,
                            format=format,
                            datefmt=date,
                            filename=cfg.get('log_path','errors.log'))
    
def main():
    #parse the users wishes
    parser = setup_argparse();
    args = vars(parser.parse_args())
     
    #determine what to do and create the argument object
    # for it. Then run it over what needs to be shot.
    if args.get('subparser_name') == prsr_SCRIPT:
        script = LSScript(args.get('input'))
        try:
            if args.get('dump', False):
                script.dumpDefault()
                return
            else:
                args.update( dict( script.run() ) )
        except IOError: # We don't want to show the man behind the curtain.
            raise IOError("LiVSs could not find file: %s"%args.get('input'))
        except: raise

    try:            
        # We now can create our LSRunner object.
        runner = LSRunner( args )
        
        # Set up logging before running!
        setup_logging( args )
    
		# Run!
        runner.run()
    except: raise
    
############################# Main functionality #############################
if __name__ == "__main__": main()
else: print(__usage__%{'prog':"livss.py"})
##############################################################################